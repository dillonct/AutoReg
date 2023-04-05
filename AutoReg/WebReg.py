import json
import urllib
import urllib3
import requests


WEBREG_STARTUP_URL = 'https://www.reg.uci.edu/cgi-bin/webreg-redirect.sh'
WEBREG_BASE_URL = 'https://webreg{}.reg.uci.edu/cgi-bin/wramia'
DUO_VERSION = 2.8
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WebReg():
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.verify = False


    def login(self, UCInetID: str, password: str) -> bool:
        # Initializing WebReg login session.
        redirect = self.session.get(WEBREG_STARTUP_URL)
        startup = self.session.get(redirect.url)

        # Parsing WebReg session info.
        session_url = self._parse_url(startup.text)
        self.num = self._get_between(session_url, 'webreg', '.reg')
        self.call = self._get_between(session_url, 'call=', '&')

        reg_data = {
            'ucinetid': UCInetID,
            'password': password, # There might be a chance to leak the user's password.
            'login_button': 'Logging in'
        }
        reg = self.session.post(session_url, data=reg_data) # https://login.uci.edu/ucinetid/webauth?return_url=https://webreg{}.reg.uci.edu:443/cgi-bin/wramia?page=login?call={}&info_text=Reg+Office+Home+Page&info_url=https://www.reg.uci.edu/


        # Requesting the user's DUO information and starting up the authorization session.
        duo_url = 'https://login.uci.edu' + self._parse_url(reg.text)
        init = self.session.get(duo_url)
        init_json = json.loads(self._get_between(init.text, 'init(', ');').replace('\'', '"'))

        # Preparing the main DUO authorization request.
        auth_url = f'https://{init_json["host"]}'
        auth_params = {
            'tx': init_json['sig_request'].split(':APP')[0],
            'parent': duo_url,
            'v': DUO_VERSION
        }
        auth = self.session.post(auth_url + '/frame/web/v1/auth?', params=auth_params)
        sid = urllib.parse.unquote(auth.url.split('sid=')[1])

        # Requesting DUO prompt by using "passcode" factor.
        prompt_data = {
            'sid': sid,
            'device': 'phone1',
            'factor': 'Passcode',
            'passcode': input('enter: '),
            'days_to_block': 'None'
        }
        prompt = self.session.post(auth_url + '/frame/prompt', data=prompt_data)

        # Requesting DUO prompt status check.
        status_data = {
            'sid': sid,
            'txid': prompt.json()['response']['txid']
        }
        status = self.session.post(auth_url + '/frame/status', data=status_data)
        status_json = status.json()


        if status_json['stat'] == 'OK' and status_json['response']['result'] == 'SUCCESS':
            success = self.session.post(auth_url + status_json['response']['result_url'], data={'sid': sid})
            wrapup_data = {
                'return_url': f'https://webreg{self.num}.reg.uci.edu:443/cgi-bin/wramia?page=login?call={self.call}&v=2.8',
                'sig_response': f'{success.json()["response"]["cookie"]}:APP{init_json["sig_request"].split(":APP")[1]}'
            }
            self.session.post('https://login.uci.edu/duo/duo_auth.php', data=wrapup_data)

            print(f'https://webreg{self.num}.reg.uci.edu/cgi-bin/wramia?page=login?call={self.call}')
            return True
        else:
            print(status_json)
            return False


    def _parse_url(self, text: str) -> str:
        return text.split('url=', 1)[1].split('">')[0]


    def _get_between(self, text: str, token1: str, token2: str) -> str:
        return text.split(token1, 1)[1].split(token2)[0]


w = WebReg()
w.login('ID','PW')