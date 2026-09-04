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

## CloudStack core findings

Current CloudStack already contains most of the storage and runtime primitives
needed for a narrow first integrity boundary:

- `extension_details` stores extension-scoped key/value metadata without a new
  database schema. Values can be marked `display=false`.
- visible extension details are forwarded to the extension as runtime
  configuration; hidden details are retained by the framework and are not
  forwarded. Hidden details are therefore the natural place for framework-owned
  provenance metadata.
- the external provisioner already calculates a SHA-512 checksum of the
  executable entry point.
- the extensions manager already compares that checksum across management
  servers and marks the extension path not ready when the executable differs.

The current mechanism therefore proves a useful but narrower statement:

> all participating management servers are executing the same entry-point bytes.

It does not yet prove:

> those entry-point bytes are the bytes an operator approved from an identified
> source revision.

That missing comparison is the first integrity anchor.

## Prior whole-directory work

Apache CloudStack PR #11814 previously expanded extension checksums from the
entry point to a deterministic per-file map for the whole extension directory.
The implementation was exercised by packaging and integration testing and is
useful prior art for a later artifact-wide identity.

It should not be copied wholesale into the first provenance change. Reusing the
existing peer checksum command with a different wire value would also create a
rolling-upgrade compatibility risk: an older management server would return an
entry-point checksum while a newer server could return a directory identity.

The first change should preserve the existing peer protocol and checksum meaning.
Whole-directory identity can be added later with an explicitly versioned or
backward-compatible mechanism.

## First core primitive

The smallest backward-compatible enforcement step is an optional expected
entry-point SHA-512 value owned by the extension framework:

1. an administrator supplies the expected SHA-512 when creating or updating an
   extension;
2. CloudStack validates the value before persisting it as hidden extension
   metadata;
3. the normal path-state check calculates the local entry-point SHA-512;
4. if an expected value exists and does not match, the extension path is not
   ready and peer checks are not treated as evidence of approval;
5. if no expected value exists, current behavior remains unchanged;
6. peer management servers continue exchanging the existing entry-point checksum
   value, preserving rolling-upgrade behavior.

This adds the missing relation:

```text
operator-approved checksum -> installed entry point -> executed entry point
```

without claiming source provenance that CloudStack has not yet recorded.

## Provenance sequence

Once the integrity anchor is proven, the next layer can record source identity
using the same framework-owned metadata channel:

```text
source URL
resolved immutable revision
artifact URL (when applicable)
artifact digest
entry-point path
expected entry-point digest
```

The expected entry-point digest remains useful even after artifact-wide
verification because it binds the executable CloudStack actually invokes to the
verified installation record.

## Required failure cases

A future implementation should reject or clearly fail installation or readiness
when:

- an expected entry-point digest is malformed;
- an expected entry-point digest does not match the installed executable;
- an expected artifact digest does not match the retrieved bytes;
- an immutable revision cannot be resolved for a mutable discovery ref;
- the configured entry point is not present in the verified artifact;
- the installed executable no longer matches the verified installed artifact;
- an extension update changes source revision or artifact digest without
  producing a new installation record.

A missing digest may be permitted only during an explicitly defined
compatibility or discovery mode. It must not be silently described as verified.

## Reference verifier

`tools/verify_extension_entrypoint.py` is an investigation-only reference
implementation for the first boundary. It accepts an entry-point path and a
128-character SHA-512 hex digest, emits a machine-readable result, and fails
closed for malformed expected digests, missing entry points, and mismatches.

The verifier is deliberately independent of the CloudStack runtime. Its purpose
is to lock down the expected comparison semantics before the corresponding core
change is proposed.

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
expected entry-point digest
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
- Firecracker-specific support in CloudStack core;
- changing the existing management-server peer checksum protocol.

Those can be layered later if the minimum immutable source-and-digest boundary is
accepted.

## Next implementation question

The next CloudStack-core patch should decide the smallest API surface for the
optional expected checksum while preserving framework ownership of the stored
value. The important property is not the eventual field name: the expected value
must not become ordinary extension runtime configuration, and a mismatch must
prevent the path from being considered ready.
