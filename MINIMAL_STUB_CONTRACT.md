# MINIMAL_STUB_CONTRACT.md - Sage sidecar scope

The `sage-stubs` sidecar is a supporting dependency for provider-MRO
projection. It is not the core plugin, and it is not responsible for making all
downstream Sage code type-clean.

## Required sidecar surface

The sidecar must expose enough Sage symbols for every provider class in a
projected MRO to resolve to a mypy `TypeInfo`.

Required surfaces are:

- Sage category infrastructure referenced by projection or generated
  manifests: `Category`, `Category_singleton`, `CategoryWithAxiom`,
  `CategoryWithParameters`, and `JoinCategory`.
- Sage object interfaces referenced by provider annotations or projected
  providers: `Parent`, `Element`, `Morphism`, and `Homset`.
- Provider containers that appear in manifest `provider_mro` values, such as
  `Sets.ParentMethods`, `Rings.ParentMethods`, `Modules.ParentMethods`,
  `VectorSpaces.ParentMethods`, and `Homsets.ParentMethods`.
- Provider methods whose signatures determine inheritance behavior for selected
  proof surfaces: `@override`, `@final`, abstract methods, and signature
  compatibility.

## Out of scope for plugin completion

The sidecar does not need comprehensive Sage typing coverage before the plugin
is complete. These are sidecar or consumer backlog items, not plugin blockers:

- Ordinary Sage methods that do not appear in projected provider MRO proof
  surfaces.
- Operator, membership, constructor, or helper signatures used only to reduce
  unrelated downstream mypy noise.
- Broad category-tree stubbing performed only to lower the total
  `category_specs` error count.

## Failure classification

Use this classification when a real consumer run fails:

| Failure | Owner | Blocks plugin completion? |
|---|---|---|
| Missing `TypeInfo` for a provider in a projected MRO | sidecar | yes |
| Manifest MRO differs from Sage runtime MRO | plugin resolver/oracle | yes |
| Mypy `TypeInfo.bases` or `TypeInfo.mro` differs from manifest projection | plugin hook | yes |
| Missing ordinary Sage method signature outside a selected proof surface | sidecar backlog | no |
| Genuine downstream type error after projection is correct | consumer repo | no |
| Unrelated broad Sage typing gap | sidecar backlog | no |

## Development policy

During active development, the plugin may depend on the latest compatible
`sage-stubs` branch for the active Sage minor version. The plugin repo must not
commit a new exact sidecar SHA for every sidecar stub addition.

Exact sidecar pins belong only to release candidates, regression bisection, or
temporary CI stabilization. Release builds should depend on a Sage-versioned
sidecar release range.
