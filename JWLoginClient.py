import re, base64, requests, execjs  # execjs 用来跑 encrypt.js
from bs4 import BeautifulSoup
from typing import Optional


class JWLoginClient:
    """哈工大（深圳）教务系统登录客户端"""
    
    # CAS 认证相关 URL
    IDS_LOGIN_URL = "https://ids.hit.edu.cn/authserver/login"
    JW_SERVICE_URL = "http://jw.hitsz.edu.cn/casLogin"
    
    def __init__(self, username: str = None, password: str = None):
        """
        初始化登录客户端
        
        Args:
            username: 学号/工号
            password: 密码
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self._is_logged_in = False
    
    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> requests.Session:
        """
        登录教务系统
        
        Args:
            username: 学号/工号，如果未提供则使用初始化时的 username
            password: 密码，如果未提供则使用初始化时的 password
            
        Returns:
            已认证的 requests.Session 对象
            
        Raises:
            ValueError: 如果未提供用户名或密码
            RuntimeError: 如果登录失败
        """
        # 使用提供的凭据或初始化时的凭据
        username = username or self.username
        password = password or self.password
        
        if not username or not password:
            raise ValueError("必须提供用户名和密码")
        
        # 步骤 1: 预请求获取登录页面和必要参数
        try:
            r = self.session.get(self.IDS_LOGIN_URL, params={'service': self.JW_SERVICE_URL})
            r.raise_for_status()
            
            dom = BeautifulSoup(r.text, "lxml")
            lt = dom.select_one("#lt")['value']
            execution = dom.select_one("input[name=execution]")['value']
            salt = dom.select_one("#pwdEncryptSalt")['value']
            
            # 步骤 2: 加密密码
            with open("/Users/doby/D/mcp-learn/mcp_hitsz_jw/encrypt.js", encoding="utf8") as f:
                ctx = execjs.compile(f.read())
            encrypted_pwd = ctx.call("encryptAES", password, salt)
            
            # 步骤 3: 提交登录表单
            payload = {
                "username": username,
                "password": encrypted_pwd,
                "passwordText": "",
                "lt": lt,
                "execution": execution,
                "_eventId": "submit",
                "dllt": "generalLogin",
                "cllt": "userNameLogin"
            }
            
            resp = self.session.post(
                self.IDS_LOGIN_URL, 
                params={'service': self.JW_SERVICE_URL},
                data=payload, 
                allow_redirects=False
            )
            
            # 检查是否成功重定向，并且包含 ticket 参数
            if resp.status_code != 302 or 'ticket=' not in resp.headers.get('Location', ''):
                raise RuntimeError("登录失败：未获取到有效的 ticket")
            
            # 步骤 4: 使用 ticket 访问教务系统完成认证
            redirect_url = resp.headers['Location']
            final_resp = self.session.get(redirect_url)
            final_resp.raise_for_status()
            
            # 检查是否有教务系统的 cookie
            if not any(c.domain == 'jw.hitsz.edu.cn' for c in self.session.cookies):
                raise RuntimeError("登录失败：未获取到教务系统的 Cookie")
            
            self._is_logged_in = True
            return self.session
            
        except requests.RequestException as e:
            raise RuntimeError(f"网络请求错误：{str(e)}")
        except (KeyError, AttributeError) as e:
            raise RuntimeError(f"解析登录页面失败：{str(e)}")
        except Exception as e:
            raise RuntimeError(f"登录过程中发生错误：{str(e)}")
    
    @property
    def is_logged_in(self) -> bool:
        """
        检查是否已登录
        
        Returns:
            bool: 是否已成功登录
        """
        return self._is_logged_in
    
    def get_session(self) -> requests.Session:
        """
        获取当前会话，如果未登录则先登录
        
        Returns:
            已认证的 requests.Session 对象
        """
        if not self._is_logged_in:
            return self.login()
        return self.session


# 使用示例
if __name__ == "__main__":
    # 方式 1: 初始化时提供凭据
    client = JWLoginClient(username="210110703", password="@96236007Sc")
    session = client.login()
    
    # 方式 2: 登录时提供凭据
    # client = JWLoginClient()
    # session = client.login(username="你的学号", password="你的密码")
    
    # 使用已认证的 session 进行后续操作
    # response = session.get("http://jw.hitsz.edu.cn/页面路径")
    # print(response.text)
