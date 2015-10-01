from cornice.resource import resource, view
from sqlalchemy.orm import joinedload, contains_eager
from pyramid.httpexceptions import HTTPConflict, HTTPNotFound, HTTPBadRequest

from c2corg_api.models.waypoint import (
    Waypoint, schema_waypoint, schema_update_waypoint)
from c2corg_api.models.document import DocumentLocale, UpdateType
from c2corg_api.models import DBSession
from c2corg_api.views.document import DocumentRest
from c2corg_api.views import validate_id, to_json_dict


@resource(collection_path='/waypoints', path='/waypoints/{id}')
class WaypointRest(DocumentRest):

    def collection_get(self):
        waypoints = DBSession. \
            query(Waypoint). \
            options(joinedload(Waypoint.locales)). \
            limit(30)

        return [to_json_dict(wp, schema_waypoint) for wp in waypoints]

    @view(validators=validate_id)
    def get(self):
        id = self.request.validated['id']
        culture = self.request.GET.get('l')
        waypoint = self._get_waypoint(id, culture)

        return to_json_dict(waypoint, schema_waypoint)

    @view(schema=schema_waypoint)
    def collection_post(self):
        waypoint = schema_waypoint.objectify(self.request.validated)

        # TODO additional validation: at least one culture, only one instance
        # for each culture

        DBSession.add(waypoint)
        DBSession.flush()

        self._create_new_version(waypoint)

        return to_json_dict(waypoint, schema_waypoint)

    @view(schema=schema_update_waypoint, validators=validate_id)
    def put(self):
        id = self.request.validated['id']
        waypoint_in = \
            schema_waypoint.objectify(self.request.validated['document'])
        self._check_document_id(id, waypoint_in.document_id)

        waypoint = self._get_waypoint(id)
        self._check_versions(waypoint, waypoint_in)
        old_versions = waypoint.get_versions()
        waypoint.update(waypoint_in)

        DBSession.merge(waypoint)
        DBSession.flush()

        (update_type, changed_langs) = \
            self._check_update_type(waypoint, old_versions)
        self._update_version(
            waypoint, self.request.validated['message'], update_type,
            changed_langs)

        return to_json_dict(waypoint, schema_waypoint)

    def _get_waypoint(self, id, culture=None):
        """Get a waypoint with either a single locale (if `culture is given)
        or with all locales.
        If no waypoint exists for the given id, a `HTTPNotFound` exception is
        raised.
        """
        if not culture:
            waypoint = DBSession. \
                query(Waypoint). \
                filter(Waypoint.document_id == id). \
                options(joinedload(Waypoint.locales)). \
                first()
        else:
            waypoint = DBSession. \
                query(Waypoint). \
                join(Waypoint.locales). \
                filter(Waypoint.document_id == id). \
                options(contains_eager(Waypoint.locales)). \
                filter(DocumentLocale.culture == culture). \
                first()

        if not waypoint:
            raise HTTPNotFound('document not found')

        return waypoint

    def _check_document_id(self, id, document_id):
        """Checks that the id given in the URL ("/waypoints/{id}") matches
        the document_id given in the request body.
        """
        if id != document_id:
            raise HTTPBadRequest(
                'id in the url does not match document_id in request body')

    def _check_versions(self, waypoint, waypoint_in):
        """Check that the passed-in document and all passed-in locales have
        the same version as the current document and locales in the database.
        If not (that is the document has changed), a `HTTPConflict` exception
        is raised.
        """
        if waypoint.version != waypoint_in.version:
            raise HTTPConflict('version of document has changed')
        for locale_in in waypoint_in.locales:
            locale = waypoint.get_locale(locale_in.culture)
            if locale:
                if locale.version != locale_in.version:
                    raise HTTPConflict(
                        'version of locale \'%s\' has changed'
                        % locale.culture)

    def _check_update_type(self, waypoint, old_versions):
        """Get the update type (only figures have changed, only locales have
        changed, both have changed or nothing).
        """
        (update_type, changed_langs) = waypoint.get_update_type(old_versions)
        if update_type == UpdateType.NONE:
            # nothing has changed, so no need to create a new version
            raise HTTPBadRequest(
                'trying do update the document with the same content')
        return (update_type, changed_langs)
