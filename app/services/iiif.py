from __future__ import annotations

from app.models.archival_object import ArchivalObject
from app.schemas.iiif import IIIFMetadataValue, IIIFReadyProfile, IIIFRights


def _metadata(profile: ArchivalObject) -> list[IIIFMetadataValue]:
    metadata: list[IIIFMetadataValue] = []
    structured = profile.intellectual_metadata

    if structured:
        if structured.language:
            metadata.append(
                IIIFMetadataValue(label="Language", value=structured.language)
            )
        if structured.genre:
            metadata.append(
                IIIFMetadataValue(label="Genre", value=", ".join(structured.genre))
            )
        if structured.edition:
            metadata.append(
                IIIFMetadataValue(label="Edition", value=structured.edition)
            )
        if structured.publisher:
            metadata.append(
                IIIFMetadataValue(label="Publisher", value=structured.publisher)
            )
        if structured.publication_date:
            metadata.append(
                IIIFMetadataValue(
                    label="Publication date", value=structured.publication_date
                )
            )
        if structured.external_identifier:
            metadata.append(
                IIIFMetadataValue(
                    label="External identifier", value=structured.external_identifier
                )
            )

    if profile.provenance:
        provenance = profile.provenance
        if provenance.source_institution:
            metadata.append(
                IIIFMetadataValue(
                    label="Source institution", value=provenance.source_institution
                )
            )
        if provenance.source_collection:
            metadata.append(
                IIIFMetadataValue(
                    label="Source collection", value=provenance.source_collection
                )
            )
        if provenance.shelfmark:
            metadata.append(
                IIIFMetadataValue(label="Shelfmark", value=provenance.shelfmark)
            )
        if provenance.accession_number:
            metadata.append(
                IIIFMetadataValue(
                    label="Accession number", value=provenance.accession_number
                )
            )

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
        required_statement = IIIFMetadataValue(
            label="Rights", value=rights.rights_statement
        )

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
        part_count=0,
        canvas_ready=False,
    )
