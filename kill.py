import aiohttp
import asyncio
import json
import re
from bs4 import BeautifulSoup
import time


from fng_logger import logger
from fng_config import config


class Kill:

    def __init__(self):
        """
        self._params = {
            'hospName': '苏州大学附属儿童医院',
            'departName': '内科(呼吸科景)',
            'doctorName': '季伟',
            'workDate': '2021-03-02',
            'workType': '上午',
            'name': '挂号人,请先维护到成员中',
            "time": "10:00",
        }
        """
        _cookie_file = open(config.get("jssz12320", "cookiefile"), 'r')
        self._headers = {
            "Host": "wx.jssz12320.cn",
            "Origin": "http://wx.jssz12320.cn",
            "User-Agent": config.get('jssz12320', 'User-Agent'),
            "X-Requested-With": "com.tencent.mm",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": _cookie_file.read()
        }
        self._params = json.loads(config.get("jssz12320", "params"))
        self._client = aiohttp.ClientSession(headers=self._headers)
        self._hosp_name_list = []
        self._depart_name_list = []
        self._user_list = None

    async def run(self):
        try:
            await self.login()
            await self.list_depart_name(self._params.get('hospName'))
            for _ in range(100):
                point = await self.work_point()
                if not point:
                    logger.info("该时间未到抢号时间, 等待0.5s")
                    await asyncio.sleep(0.5)
                    continue
                point = await self.register(**point)
                user = await self.get_user()
                if await self.sumbit_register(**point, **user):
                    logger.info("抢号成功")
                    break
        except Exception as e:
            logger.error("exception", e)
        finally:
            await self.close()



    async def login(self):
        url = "http://wx.jssz12320.cn/gh/weChatLogin.ha?redirect=register&code=041PWZ000LnsgL1auN0007IBob0PWZ0A&state=STATE"
        logger.info("GET url: %s" % url)
        async with self._client.get(url=url) as response:
            status_code = response.status
            logger.info("url: %s, status: %d" % (url, status_code))
            if status_code == 200:
                response_text = await response.text()
                logger.debug("url: %s, text: %s" % (url, response_text))
                bs = BeautifulSoup(response_text, 'html.parser')
                hospNames = bs.select('div.hospital_name')
                for hospName in hospNames:
                    self._hosp_name_list.append(hospName.string)

    def list_hosp_name(self):
        """
            data from login page
        """
        return self._hosp_name_list

    async def list_depart_name(self, hosp_name):
        url = "http://wx.jssz12320.cn/gh/register/showDepartList.ha"
        payload = "hospName=%(hospName)s&regType=expert" % {
            "hospName": hosp_name}
        logger.info("POST url: %s, payload: %s" % (url, payload))
        async with self._client.post(url=url, params=payload) as response:
            status_code = response.status
            logger.info("url: %s, status: %d" % (url, status_code))
            if status_code == 200:
                response_json = await response.json()
                logger.info("url: %s, json: %s" % (url, response_json))
                if response_json.get('status'):
                    depart_name_list = []
                    for depart in response_json.get('departList'):
                        depart_name_list.append(depart.get('departName'))
                    self._depart_name_list = depart_name_list
                    return depart_name_list

    async def work_point(self):
        """
{
  "hospName": "苏州大学附属儿童医院",
  "departName": "内科(呼吸科景)",
  "doctorName": "季伟",
  "workDate": "2021-03-02",
  "workStatus": "正常",
  "workType": "上午",
  "startTime": "10:00",
  "endTime": "10:30",
  "totalNum": 2,
  "leftNum": 0,
  "finishedNum": 0
}
        """
        points = await self.export_pool()
        if points.get('status'):
            if points.get('poolList'):
                for item in points.get('poolList'):
                    if item.get('startTime') == self._params.get('time') and item.get('leftNum') > 0:
                        return item
                    else:
                        raise Exception("该时间段的号已被抢完,请更换时间抢号")
            else:
                raise Exception("该医生<%s>的号已被抢完,请更换时间抢号" % self._params.get('workType'))
        return False

    async def export_pool(self):
        url = "http://wx.jssz12320.cn/gh/register/expertPool.ha\
?hospName=%(hospName)s&departName=%(departName)s&doctorName=%(doctorName)s&workDate=%(workDate)s&workType=%(workDate)s" % (self._params)
        logger.info("GET url: %s" % url)
        async with self._client.get(url=url) as response:
            status_code = response.status
            logger.info("url: %s, status: %d" % (url, status_code))
            if status_code == 200:
                response_text = await response.text()
                logger.debug("url: %s, text: %s" % (url, response_text))
                return await self.export_pool_list()

    async def export_pool_list(self):
        """
        {"status":true,"msg":"成功","isOpenSchedualDays":false,"workType":"上午","amStatus":true,"pmStatus":true,
        "poolList":[{"hospName":"苏州大学附属儿童医院","departName":"内科(呼吸科景)","doctorName":"季伟","workDate":"2021-03-02","workStatus":"正常","workType":"上午","startTime":"08:00","endTime":"08:30","totalNum":5,"leftNum":1,"finishedNum":0},{"hospName":"苏州大学附属儿童医院","departName":"内科(呼吸科景)","doctorName":"季伟","workDate":"2021-03-02","workStatus":"正常","workType":"上午","startTime":"08:30","endTime":"09:00","totalNum":5,"leftNum":0,"finishedNum":0},{"hospName":"苏州大学附属儿童医院","departName":"内科(呼吸科景)","doctorName":"季伟","workDate":"2021-03-02","workStatus":"正常","workType":"上午","startTime":"09:00","endTime":"09:30","totalNum":5,"leftNum":0,"finishedNum":0},{"hospName":"苏州大学附属儿童医院","departName":"内科(呼吸科景)","doctorName":"季伟","workDate":"2021-03-02","workStatus":"正常","workType":"上午","startTime":"09:30","endTime":"10:00","totalNum":3,"leftNum":0,"finishedNum":0},{"hospName":"苏州大学附属儿童医院","departName":"内科(呼吸科景)","doctorName":"季伟","workDate":"2021-03-02","workStatus":"正常","workType":"上午","startTime":"10:00","endTime":"10:30","totalNum":2,"leftNum":0,"finishedNum":0}],
        "remark":"就诊地址:景德路门诊3楼E 区提醒：进院请提前出示健康码，戴无呼吸阀口罩，与他人间隔1米距离，测体温预检后至自助机取号"}

        {"status":true,"msg":"该专家当前排班号源已满,请更换上下午或者日期查询!","fullPoolSchedule":"该专家当前排班号源已满,请更换上下午或者日期查询!",
        "isOpenSchedualDays":false,"workType":"下午","amStatus":true,"pmStatus":true,"poolList":[],
        "remark":"就诊地址:景德路门诊3楼E 区提醒：进院请提前出示健康码，戴无呼吸阀口罩，与他人间隔1米距离，测体温预检后至自助机取号"}
        """
        url = "http://wx.jssz12320.cn/gh/register/expertPoolAjax.ha"
        payload = "hospName=%(hospName)s&departName=%(departName)s&doctorName=%(doctorName)s&workDate=%(workDate)s&workType=%(workType)s" % self._params
        logger.info("POST url: %s, payload: %s" % (url, payload))
        async with self._client.post(url=url, params=payload) as response:
            status_code = response.status
            logger.info("url: %s, status: %s" % (url, status_code))
            if status_code == 200:
                response_json = await response.json()
                logger.info("url: %s, json: %s" % (url, response_json))
                return response_json

    async def register(self, **kwargs):
        """
{
  "hospName": "苏州大学附属儿童医院",
  "departName": "内科(呼吸科景)",
  "doctorName": "季伟",
  "workDate": "2021-03-02",
  "workStatus": "正常",
  "workType": "上午",
  "startTime": "10:00",
  "endTime": "10:30",
  "totalNum": 2,
  "leftNum": 0,
  "finishedNum": 0
}

    =========================== 部分html ========================================
      <input name="hosp" type="hidden" id="hospName" value="苏州大学附属儿童医院">
      <input name="depart" type="hidden" id="departName" value="内科(呼吸科景)">
      <input name="doc" type="hidden" id="doctorName" value="季伟">
      <input name="workDate" type="hidden" id="workDate" value="2021-03-02">
      <input name="workType" type="hidden" id="workType" value="上午">
      <input name="bTime" type="hidden" id="bTime" value="08:00">
      <input name="eTime" type="hidden" id="eTime" value="08:30">
      <input name="registryFee" type="hidden" id="registryFee" value="0.0">
      <input name="clinicFee" type="hidden" id="clinicFee" value="0.0">
      <input name="expertFee" type="hidden" id="expertFee" value="150.0">
      <input name="covid" type="hidden" id="covid" value="">

var checkvalue=eval('86*44');
        """
        url = "http://wx.jssz12320.cn/gh/register/register.ha"
        payload = 'hospName=%(hospName)s&departName=%(departName)s\
&doctorName=%(doctorName)s&workDate=%(workDate)s&workType=%(workType)s&beginTime=%(startTime)s&endTime=%(endTime)s' % kwargs
        logger.info("POST url: %s, payload: %s" % (url, payload))
        async with self._client.post(url=url, params=payload) as response:
            status_code = response.status
            logger.info("url: %s, status: %s" % (url, status_code))
            if status_code == 200:
                response_text = await response.text()
                logger.debug("url: %s, text: %s" % (url, response_text))
                result = {}
                match = re.findall(
                    r'var checkvalue=eval\(\'(.+)\'\);', response_text)
                if match != None and len(match) > 0:
                    result['checkvalue'] = eval(match[0])
                bs = BeautifulSoup(response_text, 'html.parser')
                result['hospName'] = bs.select('input#hospName')[
                    0].get('value')
                result['departName'] = bs.select('input#departName')[
                    0].get('value')
                result['doctorName'] = bs.select('input#doctorName')[
                    0].get('value')
                result['workDate'] = bs.select('input#workDate')[
                    0].get('value')
                result['workType'] = bs.select('input#workType')[
                    0].get('value')
                result['beginTime'] = bs.select('input#bTime')[0].get('value')
                result['endTime'] = bs.select('input#eTime')[0].get('value')
                result['registryFee'] = bs.select(
                    'input#registryFee')[0].get('value')
                result['clinicFee'] = bs.select('input#clinicFee')[
                    0].get('value')
                result['expertFee'] = bs.select('input#expertFee')[
                    0].get('value')
                result['covid'] = bs.select('input#covid')[0].get('value')
                return result

    async def get_user(self):
        if not self._user_list:
            self._user_list = await self.list_user()
        for user in self._user_list:
            if self._params['name'] == user['patientName']:
                return user

    async def list_user(self):
        """
{
    "contactInfoList": [
        {
            "age": 1,
            "birthday": null,
            "contactIdCard": "",
            "createTime": 1,
            "id": 2,
            "idCard": "",
            "insureType": "",
            "otherIdcard": null,
            "patientName": "",
            "phone": "",
            "relation": "",
            "sex": "",
            "updateTime": 1,
            "userId": "",
            "userTypeStr": "",
            "verifyStatus": null
        }
    ],
    "contactSize": 1,
    "msg": "成功",
    "self": {
        "age": 25,
        "certificationState": 0,
        "createTime": null,
        "id": 1,
        "idCard": "",
        "idCardImgUrl": null,
        "insureType": "",
        "isBlack": false,
        "isForeigners": 0,
        "password": null,
        "patientName": "",
        "phone": "",
        "rePassword": null,
        "reason": null,
        "secretAnswer": null,
        "secretQuestion": null,
        "sex": "",
        "updateTime": null,
        "usable": 1,
        "userId": "",
        "userTypeStr": ""
    },
    "status": true
}
"""
        url = "http://wx.jssz12320.cn/gh/contact/list.ha"
        logger.info("POST url: %s" % url)
        async with self._client.post(url=url) as response:
            status_code = response.status
            logger.info("url: %s, status: %s" % (url, status_code))
            if status_code == 200:
                response_json = await response.json()
                logger.info("url: %s, json: %s" % (url, response_json))
                if response_json.get('status'):
                    result = response_json.get('contactInfoList')
                    if result == None:
                        result = [] 
                    result.append(response_json.get('self'))
                    return result

    async def sumbit_register(self, **kwargs):
        """
{
    "departName": "内科(呼吸科景)",
    "doctorName": "季伟",
    "hospName": "苏州大学附属儿童医院",
    "msg": "因年龄限制，预约失败；该科室不允许大于18岁的人预约（未办户口的新生儿，父母可关注“苏州卫生12320”微信公众号，新增“新生儿”类型的联系人后进行预约挂号）",
    "selfOtherCard": null,
    "status": false,
    "workDate": "2021-03-02",
    "workType": "上午"
}
        """
        url = "http://wx.jssz12320.cn/gh/register/registerSubmit.ha"
        payload = "name=%(patientName)s&idCard=%(contactIdCard)s&phone=%(phone)s&insureType=%(insureType)s&hospName=%(hospName)s&departName=%(departName)s&\
doctorName=%(doctorName)s&workDate=%(workDate)s&workType=%(workType)s&beginTime=%(beginTime)s&endTime=%(endTime)s\
&registryFee=%(registryFee)s&clinicFee=%(clinicFee)s&expertFee=%(expertFee)s&checkvalue=%(checkvalue)d" % kwargs
        logger.info("POST url: %s, payload: %s" % (url, payload))
        async with self._client.post(url=url, params=payload) as response:
            status_code = response.status
            logger.info("url: %s, status: %s" % (url, status_code))
            if status_code == 200:
                response_json = await response.json()
                logger.info("url: %s, json: %s" % (url, response_json))
                return response_json.get('status')

    async def close(self):
        await self._client.close()


async def main():
    kill = Kill()
    await kill.run()

asyncio.run(main())
