import base64
import json
import requests
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponse

# Add missing import statements
from passerelle.base.models import BaseResource
from passerelle.utils.api import endpoint
from passerelle.utils.jsonresponse import APIError


# Define a function to validate the URL in the connector
def validate_url(value):
    if value.endswith("/"):
        raise ValidationError(
            '%(value)s ne dois pas finir avec un "/"',
            params={"value": value},
        )


# Define a class to create the connector
class ApimsCertificatsPopulationConnector(BaseResource):
    """
    Connecteur APIMS Certificats Population
    Attributes
    ----------
    url : str
        url used to connect to APIMS
    username : str
        username used to connect to APIMS
    password : str
        password used to connect to APIMS
    municipality_token : str
        token used to identify municipality to APIMS
    Methods
    -------
    """

    url = models.URLField(
        max_length=128,
        blank=True,
        verbose_name="URL",
        help_text="URL de APIMS Certificats Population",
        validators=[validate_url],
        default="https://api-staging.imio.be/bosa/v1",
    )
    username = models.CharField(
        max_length=128,
        blank=True,
        help_text="Utilisateur APIMS Certificats Population",
        verbose_name="Utilisateur",
    )
    password = models.CharField(
        max_length=128,
        blank=True,
        help_text="Mot de passe APIMS Certificats Population",
        verbose_name="Mot de passe",
    )
    municipality_token = models.CharField(
        max_length=128,
        blank=True,
        help_text="Slug d'identification de l'organisme dans APIMS Certificats Population",
        verbose_name="slug de l'instance",
    )

    category = "Connecteurs iMio"

    api_description = "Connecteur permettant d'intéragir avec APIMS Certificats Population"

    class Meta:
        verbose_name = "Connecteur APIMS Certificats Population"

    # endpoint connector
    @endpoint(
        name="read-document",
        perm="can_access",
        methods=["get"],
        description="Obtenir un certificat de population",
        parameters={
            "document_type": {
                "description": "Type de cerficats de population",
                "example_value": "LegalCohabition",
            },
            "person_nrn": {
                "description": "Numéro de registre national de la personne qui est concernée par la demande de document de type certificat de population",
                "example_value": "76070935550",
            },
            "requestor_nrn": {
                "description": "Numéro de registre national de la personne qui demande un document de type certificat de population",
                "example_value": "76070935550",
            },
        },
        display_order=1,
        display_category="Documents",
    )
    def read_document(self, request, document_type, person_nrn, requestor_nrn):
        """Get asked json document
        Parameters
        ----------
        document_type : str
            certificat type
        person_nrn : str
            National number for the extract person
        requestor_nrn : str
            National number of the requester
        Returns
        -------
        JSON
        """
        municipality_token = self.municipality_token

        url = f"{self.url}/mon-dossier-documents/{person_nrn}/{document_type}"

        self.logger.info("Récupération du PDF")
        try:
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers={"X-IMIO-REQUESTOR-NRN": requestor_nrn, "X-IMIO-MUNICIPALITY-TOKEN": municipality_token},
            )
        except Exception as e:
            self.logger.warning(f"NRN APIMS Error: {e}")
            raise APIError(f"NRN APIMS Error: {e}")
        if response.status_code == 204:
            self.logger.warning("NRN APIMS Error: 204")
            raise APIError("NRN APIMS Error: 204")

        pdf_response = None
        try:
            pdf_response = HttpResponse(response.content, content_type="application/pdf")
        except ValueError:
            self.logger.warning("NRN APIMS Error: bad PDF response")
            raise APIError("NRN APIMS Error: bad PDF response")

        try:
            response.raise_for_status()
        except Exception as e:
            self.logger.warning(f"NRN APIMS Error: {e}")
            raise APIError(f"NRN APIMS Error: {e}")
        return pdf_response
