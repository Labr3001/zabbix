#!/usr/bin/env python3
#-*-coding:utf-8-*-
import sys,logging,os,subprocess,requests
import email
import smtplib
from email.header import Header
from email.utils import formataddr
from email.mime.text import MIMEText
def logger(ip,log_name):
    logger = logging.getLogger()
    fh = logging.FileHandler(log_name)
    formater = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    fh.setFormatter(formater)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger
def ip_search(ip):
    r=requests.get('http://ip-api.com/json/%s?lang=zh-CN'%ip)
    ret = r.json()
    return (ret['regionName']+' '+ret['city'])
class sendemail:
    def __init__(self,email_list,content,subject):
        self.email_list = email_list
        self.content = content
        self.subject = subject
    def sendemail(self):
        msg = MIMEText(self.content,'plain','utf-8')
        msg['from'] = formataddr(['dark','976584601@qq.com'])
        msg['to'] = ','.join(self.email_list)
        msg['subject'] = self.subject
        service = smtplib.SMTP('smtp.qq.com')
        service.login('976584601@qq.com','password')
        service.sendmail('976584601@qq.com',self.email_list,msg.as_string())
        service.quit()
def mtr(ip,log_name):
    mtr_log_dir = os.path.dirname(os.path.realpath(sys.argv[0]))+'/mtr_log'
    cmd ='mtr -r -n -c 1 -w -b %s'%ip
    data = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf8')
    if log_name.split('/')[-1] not in os.listdir(mtr_log_dir):
        ip_city = ip_search(ip)
        title = '德国腾讯到 %s %s 线路异常'%(ip_city,ip)
        mail_list = ['cs11241991@163.com']
        mail = sendemail(mail_list,data,title)
        mail.sendemail()
    log = logger(ip,log_name)
    log.debug(data)
if __name__ =='__main__':
    ip = sys.argv[1]
    log_name = sys.argv[2]
    mtr(ip,log_name)
