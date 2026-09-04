# Extension provenance investigation

## Status

Investigation only. This document proposes the minimum evidence that should
survive an extension discovery, download, installation, and execution boundary.
It does not define the final CloudStack extension manifest format.

## Problem

CloudStack extensions are executable code. A mutable source reference such as a
Git branch is useful for discovery, but it is not sufficient to establish which
code was approved, installed, or executed.

For example, the Firecracker extension currently advertises a Git repository and
`main` as its source reference. If `main` advances after an operator reviews the
extension, the original source relationship is no longer independently
recoverable from the mutable reference alone.

## Proposed invariant

For every installed extension, CloudStack should be able to recover:

1. the source repository or distribution URL;
2. the immutable source revision used to produce the retrieved artifact;
3. the digest of the retrieved artifact;
4. the installed extension identity and version;
5. the executable entry point selected from that artifact.

A transformation from source metadata to an installed executable is trustworthy
only when this evidence survives the boundary.

## Discovery versus installation

Mutable references can remain useful for discovery:

```yaml
source:
  url: https://github.com/example/cloudstack-extension
  ref: main
```

Before installation, the reference should resolve to immutable evidence:

```yaml
source:
  url: https://github.com/example/cloudstack-extension
  revision: 0123456789abcdef0123456789abcdef01234567

artifact:
  url: https://example.invalid/cloudstack-extension.tar.gz
  sha256: <expected-sha256>

entrypoint:
  path: extension.py
```

The exact field names are intentionally not prescribed here. The invariant is
that installation and later execution must not depend only on a mutable name.

## Firecracker reference case

The existing Firecracker CloudStack extension is a useful real-world fixture:

- repository: `https://github.com/msinhore/cloudstack-firecracker-extension`
- current investigated revision: `8ebcae6724f3e047f0f05297695b420bdfdca0a1`
- entry point: `firecracker.py`
- extension type: orchestrator

Its published manifest currently names `main` as the source ref. That is fine as
a discovery pointer, but an installer should record the resolved commit and
verify the bytes retrieved for installation before executing the extension.

## Required failure cases

A future implementation should reject or clearly fail installation when:

- an expected artifact digest does not match the retrieved bytes;
- an immutable revision cannot be resolved for a mutable discovery ref;
- the configured entry point is not present in the verified artifact;
- the installed executable no longer matches the verified installed artifact;
- an extension update changes source revision or artifact digest without
  producing a new installation record.

A missing digest may be permitted only during an explicitly defined
compatibility or discovery mode. It must not be silently treated as verified.

## Evidence record

A minimal persisted record could contain values equivalent to:

```text
extension identity
extension version
source URL
resolved immutable revision
artifact URL
digest algorithm
digest value
entry point
verification result
installation timestamp
```

This record should describe what CloudStack actually installed, not merely what
a remote manifest claimed at discovery time.

## Non-goals for the first change

This investigation does not require:

- Sigstore or another signing system;
- SBOM generation;
- provenance attestations;
- a policy engine;
- a package registry;
- a redesign of the extension framework;
- Firecracker-specific support in CloudStack core.

Those can be layered later if the minimum immutable source-and-digest boundary is
accepted.

## Open implementation question

The next step is to identify the smallest existing CloudStack extension object or
installation record that can persist the resolved revision and digest without
introducing a parallel extension model. Firecracker should remain a reference
fixture for that work rather than becoming a special case in CloudStack core.
