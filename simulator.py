import os
import json
import csv
import random
import argparse
import importlib


class StakeEngineSimulator:
    def __init__(self, index_path, base_path):
        self.base_path = base_path
        self.index = self._load_json(index_path)
        self.mode = None
        self.weights = None
        self.events = None
        self.events_path = None

    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_mode(self, mode_name):
        mode = next((m for m in self.index["modes"] if m["name"] == mode_name), None)
        if not mode:
            raise ValueError(f"Mode '{mode_name}' not found")

        self.mode = mode

        weights_path = os.path.join(self.base_path, mode["weights"])
        events_path = os.path.join(self.base_path, mode["events"])

        self.weights = self._load_weights(weights_path)
        self.events = None
        self.events_path = events_path

    def _load_weights(self, path):
        ids, probs, mults = [], [], []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)

            first_row = next(reader)

            # 🔍 Detect if header exists
            has_header = any(col.lower() in ["id", "simulation_id", "probability", "weight"] for col in first_row)

            if has_header:
                # Re-read with DictReader
                f.seek(0)
                reader = csv.DictReader(f)

                headers = reader.fieldnames
                if not headers:
                    raise ValueError("CSV header row is empty")

                id_key = next((h for h in headers if h.lower() in ["simulation_id", "id", "outcome"]), None)
                prob_key = next((h for h in headers if h.lower() in ["probability", "weight", "prob"]), None)
                mult_key = next((h for h in headers if h.lower() in ["payout_multiplier", "multiplier", "payout"]), None)

                if not all([id_key, prob_key, mult_key]):
                    raise ValueError(f"Unknown CSV format. Headers: {headers}")

                print(f"Detected header format: id={id_key}, prob={prob_key}, mult={mult_key}")

                for row in reader:
                    ids.append(int(row[id_key]))
                    probs.append(float(row[prob_key]))
                    mults.append(float(row[mult_key]))

            else:
                # HEADERLESS FORMAT (your case)
                print("Detected headerless CSV format: [id, weight, multiplier]")

                # process first row
                ids.append(int(first_row[0]))
                probs.append(float(first_row[1]))
                mults.append(float(first_row[2]))

                # process rest
                for row in reader:
                    ids.append(int(row[0]))
                    probs.append(float(row[1]))
                    mults.append(float(row[2]))

        total = sum(probs)
        probs = [p / total for p in probs]

        return {
            "ids": ids,
            "probs": probs,
            "mults": mults
        }

    def _load_events(self):
        if self.events is not None:
            return

        print("Decompressing events...")
        try:
            zstd = importlib.import_module("zstandard")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "zstandard is required for --event mode. Install it with: pip install zstandard"
            ) from exc

        if not self.events_path:
            raise RuntimeError("events path is not initialized; call load_mode() first")

        with open(self.events_path, "rb") as f:
            dctx = zstd.ZstdDecompressor()
            data = dctx.decompress(f.read()).decode("utf-8")

        self.events = [json.loads(line) for line in data.splitlines()]
        print(f"Loaded {len(self.events)} events")

    def spin(self, with_event=False):
        if self.weights is None:
            raise RuntimeError("weights are not loaded; call load_mode() first")

        idx = random.choices(
            range(len(self.weights["ids"])),
            weights=self.weights["probs"],
            k=1
        )[0]

        result = {
            "simulation_id": self.weights["ids"][idx],
            "multiplier": self.weights["mults"][idx]
        }

        if with_event:
            if self.events is None:
                self._load_events()
            if self.events is None:
                raise RuntimeError("events failed to load")
            result["event"] = self.events[idx]

        return result

    def exact_rtp(self):
        if self.weights is None:
            raise RuntimeError("weights are not loaded; call load_mode() first")
        return sum(
            p * m for p, m in zip(self.weights["probs"], self.weights["mults"])
        )

    def exact_rtp_normalized(self):
        cost = float(self.mode.get("cost", 1.0)) if self.mode else 1.0
        if cost <= 0:
            raise ValueError("Mode cost must be > 0")
        return self.exact_rtp() / cost

    def simulate(self, n):
        total_return = 0

        for _ in range(n):
            total_return += self.spin()["multiplier"]

        return total_return / n

    def stats(self, n):
        results = [self.spin()["multiplier"] for _ in range(n)]
        if not results:
            raise ValueError("stats requires n > 0")

        mean = sum(results) / len(results)
        variance = sum((x - mean) ** 2 for x in results) / len(results)

        return {
            "RTP": float(mean),
            "Variance": float(variance),
            "MaxWin": float(max(results)),
            "MinWin": float(min(results))
        }

    def list_modes(self):
        return [m["name"] for m in self.index["modes"]]


# ---------------- CLI ---------------- #

def main():
    parser = argparse.ArgumentParser(description="Stake Engine Game Simulator")

    parser.add_argument("--path", required=True, help="Path to publish_files folder")
    parser.add_argument("--mode", help="Mode name")
    parser.add_argument("--all-modes", action="store_true", help="Report exact RTP for all modes")
    parser.add_argument("--target-rtp", type=float, default=96.0, help="Target RTP percentage for compliance checks")
    parser.add_argument("--rtp-tol", type=float, default=0.01, help="Allowed absolute RTP delta (percentage points)")
    parser.add_argument("--spins", type=int, default=100000, help="Number of spins")
    parser.add_argument("--stats", action="store_true", help="Show detailed stats")
    parser.add_argument("--play", action="store_true", help="Play interactive rounds")
    parser.add_argument("--event", action="store_true", help="Show full event")
    parser.add_argument("--exact", action="store_true", help="Show exact RTP from lookup weights")

    args = parser.parse_args()

    index_path = os.path.join(args.path, "index.json")

    sim = StakeEngineSimulator(index_path, args.path)

    if args.all_modes:
        print("mode,raw_mean,normalized,cost,delta_to_target,pass")
        results = []
        for mode_name in sim.list_modes():
            sim.load_mode(mode_name)
            raw = sim.exact_rtp()
            normalized = sim.exact_rtp_normalized()
            cost = float(sim.mode.get("cost", 1.0)) if sim.mode else 1.0
            delta = normalized - args.target_rtp
            passed = abs(delta) <= args.rtp_tol
            results.append(passed)
            print(
                f"{mode_name},{raw:.6f},{normalized:.6f},{cost:.6f},{delta:.6f},{passed}"
            )

        print(f"all_modes_pass: {all(results)}")
        print(f"target_rtp: {args.target_rtp:.6f}")
        print(f"tolerance: {args.rtp_tol:.6f}")
        return

    if not args.mode:
        print("Available modes:")
        for m in sim.list_modes():
            print(" -", m)
        return

    sim.load_mode(args.mode)
    if sim.mode is None:
        raise RuntimeError("failed to load mode")

    print(f"🎮 Mode: {args.mode}")

    if args.exact or (not args.play and not args.stats):
        print("Exact RTP (raw weighted mean):", round(sim.exact_rtp(), 6))
        print("Exact RTP (normalized by cost):", round(sim.exact_rtp_normalized(), 6))

    if args.play:
        print("\nInteractive mode (Ctrl+C to exit)\n")
        try:
            while True:
                input("Press ENTER to spin...")
                result = sim.spin(with_event=args.event)

                print("ID:", result["simulation_id"])
                print("Multiplier:", result["multiplier"])

                if args.event:
                    print("Event:", json.dumps(result["event"], indent=2))

                print("-" * 30)
        except KeyboardInterrupt:
            print("\n👋 Exit")

    elif args.stats:
        print("Running stats simulation...")
        stats = sim.stats(args.spins)
        mode_cost = float(sim.mode.get("cost", 1.0))
        for k, v in stats.items():
            print(f"{k}: {v:.6f}")
        print(f"RTP_Normalized_By_Cost: {stats['RTP'] / mode_cost:.6f}")

    else:
        print(f"Running RTP simulation ({args.spins} spins)...")
        rtp = sim.simulate(args.spins)
        mode_cost = float(sim.mode.get("cost", 1.0))
        print("RTP (raw mean):", round(rtp, 6))
        print("RTP (normalized by cost):", round(rtp / mode_cost, 6))


if __name__ == "__main__":
    main()