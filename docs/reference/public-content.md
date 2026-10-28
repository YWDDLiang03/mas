# Public source and research materials

[Documentation](../README.md) · [Contributing](../../CONTRIBUTING.md)

The public repository contains the implementation, general design, user guides, explicitly synthetic examples and the authorized saved system case. Documentation describes reusable mechanisms and links them to the code.

Private manuscripts, unpublished clinical text or results, draft paper figures, private comparison baselines, reviewer discussions, credentials and local workspaces stay outside Git and release assets. A public explanation can describe the method without reproducing the private material used during its development.

## Shared research copies

Scientific values, criterion definitions, candidate identities and result histories retain their recorded meaning. Where an excluded private source is named in task metadata, its descriptive title and note are replaced by a generic label in the shared copy. The content fingerprint remains available for source exclusion. The manifest lists the changed fields and original/public record digests. Local source records are preserved.

The portable capsule excludes full-text documents, model traces, private/evaluator-only records and recovery artifacts. Its manifest declares the dependency set, hashes and any metadata projection. Reusing a saved result and starting a new model investigation are separate operations in the [agent guide](../agent-run.md).

## Before publishing

1. Review the staged file list and release-asset inventory.
2. Check that private writing directories and figure working copies remain ignored.
3. Use synthetic inputs in public tests and criterion-comparison examples.
4. Run `python scripts/check_publication.py` for links, example integrity and public-content constraints.
5. Inspect new archive contents as well as repository files. Privacy changes to a published archive require a new checksum and a declared projection.

Removing content from the current tree does not erase older Git commits, tags or downloaded copies. Any history rewrite is a separate repository-maintenance operation.
