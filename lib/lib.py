from requests import Session #, models
import adal
# from importlib import import_module
import sys

def who_i_am():
    return sys._getframe(1).f_code.co_name


def get_token(authority_url, resource, username, password, client_id):
    context = adal.AuthenticationContext(
        authority_url,
        validate_authority=True
        #            , api_version=None
    )
    token_raw = context.acquire_token_with_username_password(
        resource=resource,
        username=username,
        password=password,
        client_id=client_id
    )
    token = token_raw['accessToken']
    return token


# def get_module(module=None):
#     module_object = None
#     try:
#         if module:
#             module_object = import_module(module)
#     except Exception:
#         module_object = None
#     return module_object


class API(object):
    """
    TODO: define documentation
    """

    def __init__(self):
        self.session = Session()

    def get(self, url):
        """
        TODO: define documentation
        """
        return self.__call(url)

    def add_header(self, key, value):
        self.session.headers.update({key: value})

    def reset_header(self):
        del self.session.headers

    def post(self, url, data):
        """
        Sends a POST request to the designated url, with the
        given data. Returns the POST request response.
        """
        return self.session.post(url=url, json=data)

    def __call(self, url):
        _response = self.session.get(url)
        return _response
