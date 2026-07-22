import json
import datetime
import base64
import requests

from bs4 import BeautifulSoup as BS
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

from HttpClient import HttpClientSingleton

import auth
import common
import re

import logging

logger = logging.getLogger(__name__)

class Win720:

    keySize = 128
    iterationCount = 1000
    BlockSize = 16
    keyCode = ""

    _pad = lambda self, s: s + (self.BlockSize - len(s) % self.BlockSize) * chr(self.BlockSize - len(s) % self.BlockSize)
    _unpad = lambda self, s : s[:-ord(s[len(s)-1:])]

    _REQ_HEADERS = {
        "User-Agent": auth.USER_AGENT,
        "Connection": "keep-alive",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "Origin": "https://el.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://el.dhlottery.co.kr/game/pension720/game.jsp",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "sec-ch-ua-platform": "\"Windows\"",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,ko-KR;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest"
    }

    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def buy_Win720(
        self,
        auth_ctrl: auth.AuthController,
        username: str
    ) -> dict:
        jsessionid = auth_ctrl.get_current_session_id()
        
        self.keyCode = jsessionid
        win720_round = self._get_round()
        
        makeAutoNum_ret = self._makeAutoNumbers(auth_ctrl, win720_round)
        
        try:
            q_val = json.loads(makeAutoNum_ret)['q']
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse makeAutoNum response: {makeAutoNum_ret[:100]}...")
        decrypted = self._decText(q_val)
        
        if "resultMsg" in decrypted and ":" in decrypted:
             decrypted = re.sub(r'("resultMsg":\s*)([^",}]*)([,}])', r'\1"\2"\3', decrypted)

        parsed_ret = decrypted
        try:
           extracted_num = json.loads(parsed_ret).get("selLotNo", "")
        except ValueError:
             raise ValueError(f"Failed to parse decrypted response: {repr(parsed_ret)[:200]}...")

        if not extracted_num:
             return json.loads(parsed_ret)

        orderNo, orderDate = self._doOrderRequest(auth_ctrl, win720_round, extracted_num)

        body = json.loads(self._doConnPro(auth_ctrl, win720_round, extracted_num, username, orderNo, orderDate))

        body['round'] = win720_round
        return body

    def _generate_req_headers(self, auth_ctrl: auth.AuthController) -> dict:
        return dict(self._REQ_HEADERS)
    

    def _get_round(self) -> str:
        try:
            res = self.http_client.get(
                "https://www.dhlottery.co.kr/common.do?method=main",
                headers=self._REQ_HEADERS
            )
            html = res.text
            soup = BS(html, "html5lib")
            found = soup.find("strong", id="drwNo720")
            if found:
                return str(int(found.text) - 1)
            else:
                raise ValueError("drwNo720 not found")
        except (requests.RequestException, AttributeError, ValueError):
             base_date = datetime.datetime(2024, 12, 26)
             base_round = 244
             
             today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
             
             days_ahead = (3 - today.weekday()) % 7
             next_thursday = today + datetime.timedelta(days=days_ahead)
             
             weeks = (next_thursday - base_date).days // 7
             
             return str(base_round + weeks - 1)

    def _makeAutoNumbers(self, auth_ctrl: auth.AuthController, win720_round: str) -> str:
        payload = "ROUND={}&round={}&LT_EPSD={}&SEL_NO=&BUY_CNT=&AUTO_SEL_SET=SA&SEL_CLASS=&BUY_TYPE=A&ACCS_TYPE=01".format(win720_round, win720_round, win720_round)
        headers = self._generate_req_headers(auth_ctrl)
        
        data = {
            "q": requests.utils.quote(self._encText(payload))
        }

        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/makeAutoNo.do",
            headers=headers,
            data=data,
            retries=5
        )

        return res.text

    def _doOrderRequest(self, auth_ctrl: auth.AuthController, win720_round: str, extracted_num: str) -> str:
        payload = "ROUND={}&round={}&LT_EPSD={}&AUTO_SEL_SET=SA&SEL_CLASS=&SEL_NO={}&BUY_TYPE=M&BUY_CNT=5".format(win720_round, win720_round, win720_round, extracted_num)
        headers = self._generate_req_headers(auth_ctrl)

        data = {
            "q": requests.utils.quote(self._encText(payload))
        }

        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/makeOrderNo.do",
            headers=headers,
            data=data,
            retries=5
        )

        try:
            ret = json.loads(self._decText(json.loads(res.text)['q']))
            return ret['orderNo'], ret['orderDate']
        except (json.JSONDecodeError, KeyError) as err:
             raise ValueError(f"Failed to parse doOrderRequest/decText: {res.text[:100]}...") from err

    def _doConnPro(self, auth_ctrl: auth.AuthController, win720_round: str, extracted_num: str, username: str, orderNo: str, orderDate: str) -> str:
        payload = "ROUND={}&FLAG=&BUY_KIND=01&BUY_NO={}&BUY_CNT=5&BUY_SET_TYPE=SA%2CSA%2CSA%2CSA%2CSA&BUY_TYPE=A%2CA%2CA%2CA%2CA%2C&CS_TYPE=01&orderNo={}&orderDate={}&TRANSACTION_ID=&WIN_DATE=&USER_ID={}&PAY_TYPE=&resultErrorCode=&resultErrorMsg=&resultOrderNo=&WORKING_FLAG=true&NUM_CHANGE_TYPE=&auto_process=N&set_type=SA&classnum=&selnum=&buytype=M&num1=&num2=&num3=&num4=&num5=&num6=&DSEC=34&CLOSE_DATE=&verifyYN=N&curdeposit=&curpay=5000&DROUND={}&DSEC=0&CLOSE_DATE=&verifyYN=N&lotto720_radio_group=on".format(win720_round,"".join([ "{}{}%2C".format(i,extracted_num) for i in range(1,6)])[:-3],orderNo, orderDate, username, win720_round)
        headers = self._generate_req_headers(auth_ctrl)
        
        data = {
            "q": requests.utils.quote(self._encText(payload))
        }
        
        res = self.http_client.post(
            url="https://el.dhlottery.co.kr/connPro.do",
            headers=headers,
            data=data,
            retries=5
        )

        try:
            ret = self._decText(json.loads(res.text)['q'])
        except (json.JSONDecodeError, KeyError) as err:
             raise ValueError(f"Failed to parse doConnPro: {res.text[:100]}...") from err
        else:
            return ret

    def _encText(self, plainText: str) -> str:
        encSalt = get_random_bytes(32)
        encIV = get_random_bytes(16)
        passPhrase = self.keyCode[:32]
        encKey = PBKDF2(passPhrase, encSalt, self.BlockSize, count=self.iterationCount, hmac_hash_module=SHA256)
        aes = AES.new(encKey, AES.MODE_CBC, encIV)

        plainText = self._pad(plainText).encode('utf-8')

        return "{}{}{}".format(bytes.hex(encSalt), bytes.hex(encIV), base64.b64encode(aes.encrypt(plainText)).decode('utf-8'))

    def _decText(self, encText: str) -> str:

        decSalt = bytes.fromhex(encText[0:64])
        decIv = bytes.fromhex(encText[64:96])
        cryptText = encText[96:]
        passPhrase = self.keyCode[:32]
        decKey = PBKDF2(passPhrase, decSalt, self.BlockSize, count=self.iterationCount, hmac_hash_module=SHA256)

        aes = AES.new(decKey, AES.MODE_CBC, decIv)

        decrypted_bytes = self._unpad(aes.decrypt(base64.b64decode(cryptText)))
        try:
            return decrypted_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return decrypted_bytes.decode('euc-kr')
            except UnicodeDecodeError:
                return f'{{"resultMsg": "Decryption Failed (Raw: {decrypted_bytes.hex()[:20]}...)"}}'




    # 등수별 맞은 자릿수 (뒤에서부터 하이라이트). 1등은 조까지 일치.
    _RANK_HIGHLIGHT_COUNT = {1: 6, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}

    def check_winning(self, auth_ctrl: auth.AuthController) -> dict:
        headers = self._generate_req_headers(auth_ctrl)
        parameters = common.get_search_date_range()
        no_result = {"data": "no winning data"}

        try:
            res = self.http_client.get(
                "https://www.dhlottery.co.kr/mypage/selectMyLotteryledger.do",
                params={
                    "srchStrDt": parameters["searchStartDate"],
                    "srchEndDt": parameters["searchEndDate"],
                    "ltGdsCd": "LP72",
                    "pageNum": 1,
                    "recordCountPerPage": 10
                },
                headers=headers
            )
            data = res.json().get("data", {})
            if not data.get("list"):
                return no_result

            item = data["list"][0]
            result_data = self._parse_ledger_item(item)
            result_data["win720_details"] = self._fetch_details(item.get("ntslOrdrNo"), headers)
            return result_data
        except Exception as e:
            logger.error(f"[Error] Win720 check error: {e}")
            return no_result

    def _parse_ledger_item(self, item: dict) -> dict:
        round_no = (item.get("ltEpsdView") or "").replace("회", "")

        try:
            money = f"{int(item.get('ltWnAmt') or 0):,} 원"
        except (ValueError, TypeError):
            money = "0 원"

        return {
            "round": round_no,
            "money": money,
            "purchased_date": item.get("eltOrdrDt", "-"),
            "winning_date": item.get("epsdRflDt", "-"),
            "win720_details": []
        }

    def _fetch_details(self, ntsl_ordr_no, headers: dict) -> list:
        try:
            res = self.http_client.get(
                "https://www.dhlottery.co.kr/mypage/lottery720select.do",
                params={"ntslOrdrNo": ntsl_ordr_no},
                headers=headers
            )
            detail_data = res.json()
            detail_data = detail_data.get("data", detail_data)
            return [self._format_detail_line(d) for d in detail_data.get("list", [])]
        except Exception as e:
            logger.error(f"[Error] Win720 detail error: {e}")
            return []

    def _format_detail_line(self, d_item: dict) -> dict:
        try:
            rank = int(d_item.get("wnRnk") or 0)
        except (ValueError, TypeError):
            rank = 0
        status = f"{rank}등"

        info_cn = d_item.get("ltGmInfoCn", "")
        if ":" not in info_cn:
            return {"label": "?", "result": info_cn, "status": status}

        group, number_str = info_cn.split(":", 1)
        digits = list(number_str)
        start_hl = len(digits) - self._RANK_HIGHLIGHT_COUNT.get(rank, 0)
        formatted = " ".join(
            f"[{d}]" if idx >= start_hl else f" {d} "
            for idx, d in enumerate(digits)
        )
        return {"label": f"{group}조", "result": formatted, "status": status}