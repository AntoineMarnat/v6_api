from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    ForeignKey,
    Enum
    )

from colanderalchemy import SQLAlchemySchemaNode

from c2corg_api.models import schema
from utils import copy_attributes
from document import (
    ArchiveDocument, Document, DocumentLocale, ArchiveDocumentLocale)
from c2corg_api.attributes import activities


class _ImageMixin(object):
    activities = Column(
        Enum(name='activities', inherit_schema=True, *activities),
        nullable=False)

    height = Column(SmallInteger)

    __mapper_args__ = {
        'polymorphic_identity': 'i'
    }


class Image(_ImageMixin, Document):
    """
    """
    __tablename__ = 'images'

    document_id = Column(
        Integer,
        ForeignKey(schema + '.documents.document_id'), primary_key=True)

    _ATTRIBUTES = ['activities', 'height']

    def to_archive(self):
        image = ArchiveImage()
        super(Image, self)._to_archive(image)
        copy_attributes(self, image, Image._ATTRIBUTES)

        return image


class ArchiveImage(_ImageMixin, ArchiveDocument):
    """
    """
    __tablename__ = 'images_archives'

    id = Column(
        Integer,
        ForeignKey(schema + '.documents_archives.id'), primary_key=True)


class _ImageLocaleMixin(object):

    __mapper_args__ = {
        'polymorphic_identity': 'i'
    }


class ImageLocale(_ImageLocaleMixin, DocumentLocale):
    """
    """
    __tablename__ = 'images_locales'

    id = Column(
                Integer,
                ForeignKey(schema + '.documents_locales.id'), primary_key=True)

    _ATTRIBUTES = []

    def to_archive(self):
        locale = ArchiveImageLocale()
        super(ImageLocale, self).to_archive(locale)
        copy_attributes(self, locale, ImageLocale._ATTRIBUTES)

        return locale


class ArchiveImageLocale(_ImageLocaleMixin, ArchiveDocumentLocale):
    """
    """
    __tablename__ = 'images_locales_archives'

    id = Column(
        Integer,
        ForeignKey(schema + '.documents_locales_archives.id'),
        primary_key=True)


schema_image_locale = SQLAlchemySchemaNode(
    ImageLocale,
    # whitelisted attributes
    includes=['culture', 'title', 'description'])

schema_image = SQLAlchemySchemaNode(
    Image,
    # whitelisted attributes
    includes=[
        'document_id', 'activities', 'height', 'locales'],
    overrides={
        'document_id': {
            'missing': None
        },
        'locales': {
            'children': [schema_image_locale]
        }
    })
