from __future__ import annotations

from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from app.models.archival_canvas import ArchivalCanvas
from app.models.archival_object import ArchivalObject
from app.schemas.iiif import (
    IIIFAnnotationPage,
    IIIFCanvas,
    IIIFImageBody,
    IIIFImageService,
    IIIFLanguageMap,
    IIIFManifest,
    IIIFManifestMetadata,
    IIIFMetadataValue,
    IIIFPaintingAnnotation,
    IIIFProvider,
    IIIFReadyProfile,
    IIIFRequiredStatement,
    IIIFRights,
)


def _metadata(profile: ArchivalObject) -> list[IIIFMetadataValue]:
    metadata: list[IIIFMetadataValue] = []
    structured = profile.intellectual_metadata

    if structured:
        if structured.language:
            metadata.append(IIIFMetadataValue(label="Language", value=structured.language))
        if structured.genre:
            metadata.append(IIIFMetadataValue(label="Genre", value=", ".join(structured.genre)))
        if structured.edition:
            metadata.append(IIIFMetadataValue(label="Edition", value=structured.edition))
        if structured.publisher:
            metadata.append(IIIFMetadataValue(label="Publisher", value=structured.publisher))
        if structured.publication_date:
            metadata.append(IIIFMetadataValue(label="Publication date", value=structured.publication_date))
        if structured.external_identifier:
            metadata.append(IIIFMetadataValue(label="External identifier", value=structured.external_identifier))

    if profile.provenance:
        provenance = profile.provenance
        if provenance.source_institution:
            metadata.append(IIIFMetadataValue(label="Source institution", value=provenance.source_institution))
        if provenance.source_collection:
            metadata.append(IIIFMetadataValue(label="Source collection", value=provenance.source_collection))
        if provenance.shelfmark:
            metadata.append(IIIFMetadataValue(label="Shelfmark", value=provenance.shelfmark))
        if provenance.accession_number:
            metadata.append(IIIFMetadataValue(label="Accession number", value=provenance.accession_number))

    return metadata


def build_iiif_ready_profile(obj: ArchivalObject) -> IIIFReadyProfile:
    rights = obj.rights
    rights_value = IIIFRights(
        statement=rights.rights_statement if rights else None,
        license=rights.license if rights else None,
        attribution=rights.attribution if rights else None,
    )

    required_statement = None
    if rights and rights.rights_statement:
        required_statement = IIIFMetadataValue(label="Rights", value=rights.rights_statement)

    provider: list[str] = []
    if rights and rights.rights_holder:
        provider.append(rights.rights_holder)

    return IIIFReadyProfile(
        id=obj.persistent_identifier,
        label=obj.title,
        description=obj.description,
        metadata=_metadata(obj),
        rights=rights_value,
        required_statement=required_statement,
        provider=provider,
        part_count=len(obj.canvases),
        canvas_ready=bool(obj.canvases),
    )


def _language_map(value: str) -> IIIFLanguageMap:
    return IIIFLanguageMap(en=[value])


def _manifest_metadata(obj: ArchivalObject) -> list[IIIFManifestMetadata]:
    return [
        IIIFManifestMetadata(label=_language_map(item.label), value=_language_map(item.value))
        for item in _metadata(obj)
    ]


def _canvas_id(manifest_id: str, canvas: ArchivalCanvas) -> str:
    return urljoin(manifest_id.rstrip("/") + "/", f"canvas/{canvas.canvas_identifier}")


def _build_canvas(manifest_id: str, canvas: ArchivalCanvas) -> IIIFCanvas:
    annotation_pages: list[IIIFAnnotationPage] = []
    asset = canvas.asset

    if (
        asset
        and asset.mime_type.startswith("image/")
        and asset.asset_role == "access"
        and asset.is_current
        and (not canvas.archival_object.rights or canvas.archival_object.rights.view_allowed is not False)
    ):
        parsed_manifest = urlsplit(manifest_id)
        service_id = urlunsplit(
            (
                parsed_manifest.scheme,
                parsed_manifest.netloc,
                f"/iiif/3/{quote(canvas.canvas_identifier, safe=':._-')}",
                "",
                "",
            )
        )
        image_id = urljoin(service_id.rstrip("/") + "/", "full/max/0/default.jpg")
        annotation_pages.append(
            IIIFAnnotationPage(
                id=urljoin(_canvas_id(manifest_id, canvas).rstrip("/") + "/", "page/1"),
                items=[
                    IIIFPaintingAnnotation(
                        id=urljoin(_canvas_id(manifest_id, canvas).rstrip("/") + "/", "annotation/1"),
                        body=IIIFImageBody(
                            id=image_id,
                            format="image/jpeg",
                            width=canvas.width,
                            height=canvas.height,
                            service=[IIIFImageService(id=service_id)],
                        ),
                    )
                ],
            )
        )

    return IIIFCanvas(
        id=_canvas_id(manifest_id, canvas),
        label=_language_map(canvas.label),
        width=canvas.width,
        height=canvas.height,
        duration=canvas.duration_seconds,
        items=annotation_pages,
    )


def _http_uri(value: str | None) -> str | None:
    if value and (value.startswith("https://") or value.startswith("http://")):
        return value
    return None


def build_iiif_manifest(obj: ArchivalObject, manifest_id: str) -> IIIFManifest:
    rights = obj.rights
    required_statement = None
    if rights and rights.rights_statement:
        required_statement = IIIFRequiredStatement(
            label=_language_map("Rights"),
            value=_language_map(rights.rights_statement),
        )

    providers: list[IIIFProvider] = []
    if rights and rights.rights_holder:
        providers.append(
            IIIFProvider(
                label=_language_map(rights.rights_holder),
            )
        )

    return IIIFManifest(
        id=manifest_id,
        label=_language_map(obj.title),
        description=_language_map(obj.description) if obj.description else None,
        metadata=_manifest_metadata(obj),
        rights=_http_uri(rights.license) if rights else None,
        required_statement=required_statement,
        provider=providers,
        items=[_build_canvas(manifest_id, canvas) for canvas in obj.canvases],
    )
