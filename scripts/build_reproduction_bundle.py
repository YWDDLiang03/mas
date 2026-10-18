"""Build the bounded oral multi-target capsule from an existing read-only store."""
from __future__ import annotations

import argparse
import json

from mas.core.reproduction import DEFAULT_RUN, DEFAULT_SNAPSHOT, DEFAULT_TASK, build_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', default='var/primary/store')
    parser.add_argument('--task', default=DEFAULT_TASK)
    parser.add_argument('--run', default=DEFAULT_RUN)
    parser.add_argument('--snapshot', default=DEFAULT_SNAPSHOT)
    parser.add_argument('--workflow', default='wf_cb4caec3dec348908fb3d34eae5b11d1')
    parser.add_argument('--out', default='var/reproduction-build/release')
    args = parser.parse_args(argv)
    manifest = build_bundle(args.store, args.out, task_id=args.task, run_id=args.run,
                            snapshot_id=args.snapshot, workflow_id=args.workflow,
                            progress=lambda text: print(text, flush=True))
    print(json.dumps({'capsule': manifest['capsule'], 'counts': manifest['counts']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
