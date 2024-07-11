#!/usr/bin/env python3
#-*-coding:utf-8-*-
from collections import deque
import itertools,time
import queue,json
import argparse,sys,re,os,subprocess
import time,socket,random,string
import threading
from functools import reduce
import logging

ipqli=deque()
filename = os.path.realpath(sys.argv[0])
def logger():
    dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    log_name = dir+'/log'
    logger = logging.getLogger()
    fh = logging.FileHandler(log_name)
    formater = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    fh.setFormatter(formater)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger
log = logger()
#ping程序，避免系统权限问题未使用ping3
class Ping:
    def __init__(self,ip,count=20,udp_length=64):
        ip = tuple(ip)
        self.sip,self.tip,self.type,self.port,self.inver=ip
        self.type = self.type.lower()
        self.port = int(self.port)
        self.count=count
        self.inver = float(self.inver)
        self.udp_length=udp_length
        restime_name = 'restime_deque'+''.join(ip).replace('.','')
        pkloss_name = 'pkloss_deque'+''.join(ip).replace('.','')
        ipqevent = 'event'+''.join(ip).replace('.','')
        locals()[restime_name] = deque(maxlen=60)
        locals()[pkloss_name] = deque(maxlen=60)
        self.restime_deque = locals()[restime_name]
        self.pkloss_deque = locals()[pkloss_name]
        self.ret_restime_deque = globals()[restime_name]
        self.ret_pkloss_deque = globals()[pkloss_name]
        self.ipqevent = globals()[ipqevent]
        self.compile= r'(?<=time=)\d+\.?\d+(?= ms)'
    def _tcp(self):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            start_time = time.time()
            res_count=0
            try:
                s.bind((self.sip,0))
                s.connect((self.tip, self.port))
                s.shutdown(socket.SHUT_RD)
                value = (time.time() - start_time)*1000  
                self.restime_deque.append(value)
                self.pkloss_deque.append(0)
                res_count=1
            except (socket.timeout,ConnectionError):
                self.restime_deque.append(0)
                self.pkloss_deque.append(1)
            except OSError as e:
                log.debug(e)
                return 0,0
            usetime = time.time()-start_time
            sleep_time = self.inver - usetime if usetime<self.inver else self.inver
            return sleep_time,res_count
    def _udp(self):
        res_count=0
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.settimeout(1)
        start_time = time.time()
        data=''.join(random.choice(string.ascii_letters+ string.digits) for x in range(self.udp_length))
        try:
            s.sendto(data.encode('utf-8'),(self.tip,self.port))
            s.recv(1024)
            value = (time.time() - start_time)*1000

            self.restime_deque.append(value)
            self.pkloss_deque.append(0)
            res_count=1
        except socket.timeout:
            self.restime_deque.append(0)
            self.pkloss_deque.append(1)
        except OSError as e:
            log.debug(e)
            return 0,0
        usetime = time.time()-start_time
        sleep_time = self.inver - usetime if usetime<self.inver else self.inver
        return sleep_time,res_count
    def _icmp(self):
        res_count=0
        start_time = time.time()
        cmd = 'ping -i %s -c 1 -W 1 -I %s %s'%(self.inver,self.sip,self.tip)
        ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0].decode('utf8')
        try:
            value=re.findall(self.compile, ret,re.S)[0]
            self.restime_deque.append(value)
            self.pkloss_deque.append(0)
            res_count=1
        except:
            self.pkloss_deque.append(1)
            self.restime_deque.append(0)
        usetime = time.time()-start_time
        sleep_time = self.inver - usetime if usetime<self.inver else self.inver
        return sleep_time,res_count
    def fastping(self):
        getattr(self, '_'+self.type)()
    def slow_ping(self):
        index = 0
        res_count=0
        self.ipqevent.set()
        while index<self.count:
            sleep_time,count=getattr(self, '_'+self.type)()
            index+=1
            res_count+=count
            if len(self.ret_restime_deque)<2 or len(self.ret_pkloss_deque)<2 :
                break
            time.sleep(sleep_time)
        return index,res_count
    def ping_value(self):
        start_time = time.time()
        count = self.count
        rescount = self.count
        if len(self.ret_restime_deque)<2 or len(self.ret_pkloss_deque)<2:
            fastli=[]
            for x in range(self.count):
                t = threading.Thread(target=self.fastping)
                t.start()
                fastli.append(t)
            for th in fastli:
                th.join()
        else:
            count,rescount = self.slow_ping()
            rescount=count if rescount==0 else rescount
        use_time = round(time.time()-start_time,4)
        li = [self.restime_deque.pop() for x in range(count)]
        pkli = [self.pkloss_deque.pop() for x in range(count)]
        try:
            restime = reduce(lambda x ,y :round(float(x)+float(y),2), li)/rescount if len(li) >1 else round(float(li[0]),2)
            pkloss= reduce(lambda x ,y :int(x)+int(y), pkli)/count*100
            return (round(restime,2),round(pkloss,2),use_time)   
        except Exception as e:
            log.debug(e)
            return 0,0,0
#server端代码
class Server():
    def __init__(self,sock):
        global ipqli
        self.ipqli=ipqli
        self.thli=[]
        self.ipli = []
        self.sock=sock
        self.basedir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.env = threading.Event()
    @classmethod
    def start(cls):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        address = ('127.0.0.1',6590)
        s.bind(address)
        obj = cls(s)
        ping_server=threading.Thread(target=obj.server)
        ping_server.start()
        obj.thli.append(ping_server)
        create_t = threading.Thread(target=obj.create)
        create_t.start()
        obj.thli.append(create_t)
        for t in obj.thli:
            t.join()
    def server(self):
        while True:
            try:
                self.sock.listen(100)
                conn,addr = self.sock.accept() 
                data=conn.recv(1024) 
                data = data.decode('utf-8')
                data = json.loads(data)
                ip,item = data
                restime_ipq = 'restime_deque'+''.join(ip).replace('.','')
                pkloss_ipq = 'pkloss_deque'+''.join(ip).replace('.','')
                ipqevent = 'event'+''.join(ip).replace('.','')
                if ip not in self.ipli:
                    globals()[restime_ipq] = deque(maxlen=30)
                    globals()[pkloss_ipq] = deque(maxlen=30)
                    globals()[ipqevent] = threading.Event()
                    self.ipqli.append(ip)
                    self.ipli.append(ip)
                    log.debug('create ipdeque %s %s'%(restime_ipq,pkloss_ipq))
                    self.env.set()
                self.sendvalue(conn,ip,item)
                conn.close()
            except Exception as e:
                log.debug(str(e))
                conn.close()
    def create(self):
        while True:
            self.env.wait()
            try:
                ip = self.ipqli.pop()
                log.debug('create %s'%ip)
                t=threading.Thread(target=self.makevalue,args=(ip,))
                t.start()
            except Exception as a:
                log.debug(str(a))
            if not self.ipqli:
                self.env.clear()
            
    def makevalue(self,ip):
        restime_name = 'restime_deque'+''.join(ip).replace('.','')
        pkloss_name = 'pkloss_deque'+''.join(ip).replace('.','')
        ipqevent_name = 'event'+''.join(ip).replace('.','')
        restime_ipq = globals()[restime_name]
        pkloss_ipq = globals()[pkloss_name]
        ipqevent = globals()[ipqevent_name]
        obj = Ping(ip)
        while len(restime_ipq) < 30 or len(pkloss_ipq) <30:
                restime,pkloss,use_time=obj.ping_value()            
                restime_ipq.append((restime,use_time))
                pkloss_ipq.append((pkloss,use_time))   
        else:
            del restime_ipq
            del pkloss_ipq
            del ipqevent
            self.ipli.remove(ip)
            log.debug('delete ipdeque %s %s'%(restime_name,pkloss_name))
    def sendvalue(self,conn,ip,item):
        fromat_ip=''.join(ip).replace('.','')
        _,tip,*arg=ip
        restime_name = 'restime_deque'+fromat_ip
        pkloss_name = 'pkloss_deque'+fromat_ip
        ipqevent_name = 'event'+fromat_ip
        restime_ipq = globals()[restime_name]
        pkloss_ipq = globals()[pkloss_name]
        ipqevent = globals()[ipqevent_name]
        mtr_dir = self.basedir+'/mtr_log/'+tip+'-'+time.strftime('%Y-%m-%d',time.localtime()) + '.log'
        mtr_cmd = self.basedir + '/mtr.py'+' '+tip+' '+mtr_dir
        if len(restime_ipq) < 2 and len(restime_ipq) <2:
            ipqevent.clear()
        try:
            ipqevent.wait()
            if item =='restime':
                ret,use_time = restime_ipq.pop()
                hisret,_=restime_ipq[-1]
                if ret - hisret >20:
                    subprocess.Popen(mtr_cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            elif item =='pkloss':
                ret,use_time = pkloss_ipq.pop()
                if 100> ret  >20:
                    subprocess.Popen(mtr_cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        except Exception as a:
            ret = a
            log.debug(str(ret))
        conn.sendall(str(ret).encode())

#用户输入IP格式检查
class Ipcheck():
    def __init__(self,sip,tip,item,ping_type,inver):
        self.sip =sip
        self.tip=tip
        self.item=item
        self.type = ping_type.lower()
        self.inver=float(inver)
    def check(self):
        if self.item not in ['restime','pkloss'] or self.type not in ['icmp','tcp','udp'] or self.inver<0.2:
            return False
        elif not self.checkipformat():
            return False
        else:
            return True
    def check_fun(self,ip):
        return int(ip)<256
    def checkipformat(self):
        try:
            tiplist = self.tip.split('.')
            tipformat = re.findall(r'^\d+\.\d+\.\d+\.\d+$', self.tip)
            if  self.sip:
                siplist = self.sip.split('.')
                sipformat = re.findall(r'^\d+\.\d+\.\d+\.\d+$', self.sip)
            else:
                siplist=[1,1,1,1]
                sipformat=True
            if not tipformat or not sipformat:
                raise
            check_ipli = tiplist+siplist
            return self.checkiplength(check_ipli)
        except:
            return False
    def checkiplength(self,check_ipli):
        if list(itertools.filterfalse(self.check_fun, check_ipli)):
            return False
        else:
            return True        
def run():
    
    cmd = 'python3 %s -S server'%filename
    subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#socket_client端，向server请求数据并返回给用户
def socket_client(ip,item):
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(('127.0.0.1',6590))
        data = [ip,item]
        data = json.dumps(data)
        s.sendall(data.encode())
        ret = s.recv(1024)
        s.close()
        print(ret.decode())
    except socket.timeout as t:
        log.debug(str(t))
        s.close()
        sys.exit(0)
    except Exception as e:
        print('server will start')
        log.debug(str(e))
        sys.exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='icmp for monitor')
    parser.add_argument('-S',action = 'store',dest='server')
    parser.add_argument('-t',action = 'store',dest='tip')
    parser.add_argument('-s',action = 'store',dest='sip')
    parser.add_argument('-I',action='store',dest='item')
    parser.add_argument('-i',action='store',dest='inver',default='1')
    parser.add_argument('-T',action='store',dest='ping_type',default='icmp')
    parser.add_argument('-p',action='store',dest='port',default='0')
    args= parser.parse_args()
    server_status_cmd = "ps -ef | grep '%s -S server' | grep -v grep | cut -c 9-16"%filename
    server_status  = subprocess.Popen(server_status_cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
    if not server_status:
        run()
    if args.server:
        Server.start()
        sys.exit(0)
    try:
        tip = socket.gethostbyname(args.tip)
        sip = args.sip
        item = args.item
        ping_type = args.ping_type
        port = args.port
        inver=args.inver
        ip=(sip,tip,ping_type,port,inver)
    except:
        print('format error')
    check = Ipcheck(sip, tip, item,ping_type,inver)
    if not check.check():
        print('''---------------------------Options-----------------------------------
-s --source ip address
-t --destination ip address
-I --item(restime/pkloss)
-T --type(icmp/tcp/udp default icmp)
-p --port(default 0)
-i --inver(default 1/min 0.2)
---------------------------Example-----------------------------------
------pingd -s 10.0.3.108 -t 10.0.0.1 -I restime -i 1 -T tcp -p 80-------
        ''')
        sys.exit(0)
    socket_client(ip,item)
