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
            params={'value': value},
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
    municipality_nis_code : str
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
        default="https://api-staging.imio.be/bosa/v1"
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
    municipality_nis_code = models.CharField(
        max_length=128,
        blank=True,
        help_text="Code NIS d'identification de l'organisme dans APIMS Certificats Population",
        verbose_name="Code NIS de l'organisme",
    )

    category = 'Connecteurs iMio'

    api_description = "Connecteur permettant d'intéragir avec APIMS Certificats Population"

    class Meta:
        verbose_name = 'Connecteur APIMS Certificats Population'
    # Define a method that gives an access to http session
    @property
    def session(self):
        session = requests.Session()
        session.auth = (self.username, self.password)
        session.headers.update({
            "Accept": "application/json",
            "X-IMIO-MUNICIPALITY-NIS": self.municipality_nis_code
        })
        return session

    # endpoint connector
    @endpoint(
        name="document-types",
        perm="can_access",
        methods=["get"],
        description="Obtenir un certificat de population",
        parameters={
            "document_type": {
                "description": "Type de cerficat de population",
                "example_value": "LegalCohabition",
            },
            "person_nrn": {
                "description": "Numéro de registre national de la personne qui est concernée par la demande de document de type certificat de population",
                "example_value": "15010123487",
            },
            "requestor_nrn": {
                "description": "Numéro de registre national de la personne qui demande un document de type certificat de population",
                "example_value": "15010123487",
            },
            "commune_nis": {
                "description": "Code NIS de la commune",
                "example_value": "51063",
            },
        },
        display_order=1,
        display_category="Documents"
    )
    def get_document(self, request, document_type, person_nrn, requestor_nrn, commune_nis=None, language="fr"):
        """ Get asked json document
        Parameters
        ----------
        document_type : str
            Extract's code
        person_nrn : str
            National number for the extract person
        requestor_nrn : str
            National number of the requester
        language : str
            Language of the document
        Returns
        -------
        JSON
        """
        if commune_nis is None:
            commune_nis = self.municipality_nis_code

        url = f"{self.url}/mon-dossier-documents/{person_nrn}/{document_type}"

        self.logger.info("Récupération du JSON")
        try:
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers={
                    "X-IMIO-REQUESTOR-NRN": requestor_nrn,
                    "X-IMIO-MUNICIPALITY-NIS": commune_nis
                },
                params={"language": language}
            )
        except Exception as e:
            self.logger.warning(f'certificats population APIMS Error: {e}')
            raise APIError(f'certificats population APIMS Error: {e}')

        json_response = None
        try:
            json_response = response.json()
        except ValueError:
            self.logger.warning('certificats population APIMS Error: bad JSON response')
            raise APIError('certificats population APIMS Error: bad JSON response')

        if response.status_code >= 500:
            self.logger.warning(f'certificats population APIMS Error: {e} {json_response}')
            raise APIError(f'certificats population APIMS Error: {e} {json_response}')

        return json_response

    @endpoint(
        name="decode-extract",
        perm="can_access",
        methods=["post"],
        description="Décoder le certificats population d'une personne",
        display_order=1,
        display_category="Documents"
    )
    def decode_extract(self, request):
        """ Post decode document as PDF
        Returns
        -------
        PDF document
        """

        self.logger.info("certificats population decode pdf base64")
        body = json.loads(request.body)
        pdf_base64 = body["pdf_base64"]

        pdf_response = None
        try:
            pdf = base64.b64decode(pdf_base64)
            pdf_response = HttpResponse(pdf, content_type="application/pdf")
        except ValueError:
            self.logger.warning('certificats population APIMS Error: bad PDF response')
            raise APIError('certificats population APIMS Error: bad PDF response')

        return pdf_response