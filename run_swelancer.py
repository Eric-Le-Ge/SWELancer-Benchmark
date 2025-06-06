from __future__ import annotations

import os
import json
# Load environment before importing anything else
from dotenv import load_dotenv
load_dotenv()

from swelancer import SWELancerEval 
import argparse
import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.recorder import dummy_recorder
from nanoeval.setup import nanoeval_entrypoint
from swelancer_agent import SimpleAgentSolver

LOG_DIR = os.getenv('LOG_DIR')

def parse_args():
    parser = argparse.ArgumentParser(description='Run SWELancer evaluation')
    parser.add_argument('--issue_ids', nargs='*', type=str, help='List of ISSUE_IDs to evaluate. If not specified, all issues will be evaluated.')
    return parser.parse_args()

async def main() -> None:
    args = parse_args()
    taskset = args.issue_ids if args.issue_ids else None
    model = os.environ["MODEL"]

    report = await nanoeval.run(
        EvalSpec(
            # taskset is a list of ISSUE_IDs you wish to evaluate (e.g., ["123", "456_789"])
            eval=SWELancerEval(
                solver=SimpleAgentSolver(model=model),
                taskset=taskset
            ),
            runner=RunnerArgs(
                concurrency=25,
                experimental_use_multiprocessing=True,
                enable_slackbot=False,
                recorder=dummy_recorder(),
                max_retries=5
            ),
        )
    )
    print(report)
    # Export report.
    if LOG_DIR:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, 'output.jsonl'), 'w') as f:
            f.write(json.dumps(report))


if __name__ == "__main__":
    nanoeval_entrypoint(main())
