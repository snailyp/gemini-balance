import requests
from app.domain.image_models import ImageMetadata, ImageUploader, UploadResponse
from enum import Enum
from typing import Optional, Any
import hashlib
import base64
import hmac
from datetime import datetime
from urllib.parse import quote
from app.log.logger import get_image_create_logger

class UploadErrorType(Enum):
    """上传错误类型枚举"""
    NETWORK_ERROR = "network_error"  # 网络请求错误
    AUTH_ERROR = "auth_error"        # 认证错误
    INVALID_FILE = "invalid_file"    # 无效文件
    SERVER_ERROR = "server_error"    # 服务器错误
    PARSE_ERROR = "parse_error"      # 响应解析错误
    UNKNOWN = "unknown"              # 未知错误


class UploadError(Exception):
    """图片上传错误异常类"""
    
    def __init__(
        self,
        message: str,
        error_type: UploadErrorType = UploadErrorType.UNKNOWN,
        status_code: Optional[int] = None,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ):
        """
        初始化上传错误异常
        
        Args:
            message: 错误消息
            error_type: 错误类型
            status_code: HTTP状态码
            details: 详细错误信息
            original_error: 原始异常
        """
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        self.original_error = original_error
        
        # 构建完整错误信息
        full_message = f"[{error_type.value}] {message}"
        if status_code:
            full_message = f"{full_message} (Status: {status_code})"
        if details:
            full_message = f"{full_message} - Details: {details}"
            
        super().__init__(full_message)
    
    @classmethod
    def from_response(cls, response: Any, message: Optional[str] = None) -> "UploadError":
        """
        从HTTP响应创建错误实例
        
        Args:
            response: HTTP响应对象
            message: 自定义错误消息
        """
        try:
            error_data = response.json()
            details = error_data.get("data", {})
            return cls(
                message=message or error_data.get("message", "Unknown error"),
                error_type=UploadErrorType.SERVER_ERROR,
                status_code=response.status_code,
                details=details
            )
        except Exception:
            return cls(
                message=message or "Failed to parse error response",
                error_type=UploadErrorType.PARSE_ERROR,
                status_code=response.status_code
            )


class SmMsUploader(ImageUploader):
    API_URL = "https://sm.ms/api/v2/upload"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def upload(self, file: bytes, filename: str) -> UploadResponse:
        try:
            # 准备请求头
            headers = {
                "Authorization": f"Basic {self.api_key}"
            }
            
            # 准备文件数据
            files = {
                "smfile": (filename, file, "image/png")
            }
            
            # 发送请求
            response = requests.post(
                self.API_URL,
                headers=headers,
                files=files
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 验证上传是否成功
            if not result.get("success"):
                raise UploadError(result.get("message", "Upload failed"))
                
            # 转换为统一格式
            data = result["data"]
            image_metadata = ImageMetadata(
                width=data["width"],
                height=data["height"],
                filename=data["filename"],
                size=data["size"],
                url=data["url"],
                delete_url=data["delete"]
            )
            
            return UploadResponse(
                success=True,
                code="success",
                message="Upload success",
                data=image_metadata
            )
            
        except requests.RequestException as e:
            # 处理网络请求相关错误
            raise UploadError(f"Upload request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            # 处理响应解析错误
            raise UploadError(f"Invalid response format: {str(e)}")
        except Exception as e:
            # 处理其他未预期的错误
            raise UploadError(f"Upload failed: {str(e)}")
    
    
class QiniuUploader(ImageUploader):
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        
    def upload(self, file: bytes, filename: str) -> UploadResponse:
        # 实现七牛云的具体上传逻辑
        pass
    
    
class PicGoUploader(ImageUploader):
    """Chevereto API 图片上传器"""
    
    def __init__(self, api_key: str, api_url: str = "https://www.picgo.net/api/1/upload"):
        """
        初始化 Chevereto 上传器
        
        Args:
            api_key: Chevereto API 密钥
            api_url: Chevereto API 上传地址
        """
        self.api_key = api_key
        self.api_url = api_url
        
    def upload(self, file: bytes, filename: str) -> UploadResponse:
        """
        上传图片到 Chevereto 服务
        
        Args:
            file: 图片文件二进制数据
            filename: 文件名
            
        Returns:
            UploadResponse: 上传响应对象
            
        Raises:
            UploadError: 上传失败时抛出异常
        """
        try:
            # 准备请求头
            headers = {}
            
            # 构建请求URL
            request_url = self.api_url
            
            # 判断是否为默认PicGo URL，如果是则使用header认证，否则使用URL参数认证
            if self.api_url == "https://www.picgo.net/api/1/upload":
                headers["X-API-Key"] = self.api_key
            else:
                # 对于自定义URL，将API key作为查询参数添加到URL中
                from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
                parsed_url = urlparse(request_url)
                query_params = parse_qs(parsed_url.query)
                query_params["key"] = self.api_key
                new_query = urlencode(query_params, doseq=True)
                request_url = urlunparse(parsed_url._replace(query=new_query))
            
            # 准备文件数据
            files = {
                "source": (filename, file)
            }
            
            # 发送请求
            response = requests.post(
                request_url,
                headers=headers,
                files=files
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 处理自定义PicGo服务器的响应格式
            if "success" in result and "result" in result:
                # 自定义PicGo服务器格式: {"success": true, "result": ["url"]}
                if result["success"]:
                    image_url = result["result"][0] if result["result"] and len(result["result"]) > 0 else ""
                    image_metadata = ImageMetadata(
                        width=0,
                        height=0,
                        filename=filename,
                        size=0,
                        url=image_url,
                        delete_url=None
                    )
                    return UploadResponse(
                        success=True,
                        code="success",
                        message="Upload success",
                        data=image_metadata
                    )
                else:
                    raise UploadError(
                        message="Upload failed",
                        error_type=UploadErrorType.SERVER_ERROR,
                        status_code=400,
                        details=result
                    )
            
            # 处理官方PicGo服务器的响应格式
            # 验证上传是否成功
            if result.get("status_code") != 200:
                error_message = "Upload failed"
                if "error" in result:
                    error_message = result["error"].get("message", error_message)
                raise UploadError(
                    message=error_message,
                    error_type=UploadErrorType.SERVER_ERROR,
                    status_code=result.get("status_code"),
                    details=result.get("error")
                )
                
            # 从响应中提取图片信息
            image_data = result.get("image", {})
            
            # 构建图片元数据
            image_metadata = ImageMetadata(
                width=image_data.get("width", 0),
                height=image_data.get("height", 0),
                filename=image_data.get("filename", filename),
                size=image_data.get("size", 0),
                url=image_data.get("url", ""),
                delete_url=image_data.get("delete_url", None)
            )
            
            return UploadResponse(
                success=True,
                code="success",
                message=result.get("success", {}).get("message", "Upload success"),
                data=image_metadata
            )
            
        except requests.RequestException as e:
            # 处理网络请求相关错误
            raise UploadError(
                message=f"Upload request failed: {str(e)}",
                error_type=UploadErrorType.NETWORK_ERROR,
                original_error=e
            )
        except (KeyError, ValueError, TypeError) as e:
            # 处理响应解析错误
            raise UploadError(
                message=f"Invalid response format: {str(e)}",
                error_type=UploadErrorType.PARSE_ERROR,
                original_error=e
            )
        except UploadError:
            # 重新抛出已经是 UploadError 类型的异常
            raise
        except Exception as e:
            # 处理其他未预期的错误
            raise UploadError(
                message=f"Upload failed: {str(e)}",
                error_type=UploadErrorType.UNKNOWN,
                original_error=e
            )


class AliyunOSSUploader(ImageUploader):
    """阿里云OSS图片上传器"""
    
    def __init__(self, access_key: str, access_key_secret: str, bucket_name: str, 
                 endpoint: str, region: str, use_internal: bool = False):
        """
        初始化阿里云OSS上传器
        
        Args:
            access_key: OSS访问密钥ID
            access_key_secret: OSS访问密钥
            bucket_name: OSS存储桶名称
            endpoint: OSS端点地址
            region: OSS区域
            use_internal: 是否使用内网端点
        """
        self.access_key = access_key
        self.access_key_secret = access_key_secret
        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.region = region
        self.use_internal = use_internal
        self.logger = get_image_create_logger()
        
        # 构建请求URL
        if not endpoint.startswith(('http://', 'https://')):
            self.base_url = f"https://{bucket_name}.{endpoint}"
        else:
            self.base_url = f"{endpoint}/{bucket_name}"
            
        self.logger.info(f"Initialized AliyunOSSUploader for bucket: {bucket_name}, region: {region}")
    
    def _sign_request(self, method: str, path: str, headers: dict, content: bytes = b'') -> dict:
        """
        为OSS请求生成签名
        
        Args:
            method: HTTP方法
            path: 请求路径
            headers: 请求头
            content: 请求内容
            
        Returns:
            包含签名的请求头
        """
        # 计算Content-MD5
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode('utf-8') if content else ''
        
        # 设置日期
        date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 更新headers
        headers['Date'] = date
        if content_md5:
            headers['Content-MD5'] = content_md5
        headers['Content-Type'] = headers.get('Content-Type', 'image/png')
        
        # 构建CanonicalizedOSSHeaders
        oss_headers = []
        for key, value in sorted(headers.items()):
            if key.lower().startswith('x-oss-'):
                oss_headers.append(f"{key.lower()}:{value}")
        canonicalized_oss_headers = '\n'.join(oss_headers)
        if canonicalized_oss_headers:
            canonicalized_oss_headers += '\n'
        
        # 构建CanonicalizedResource
        canonicalized_resource = f"/{self.bucket_name}{path}"
        
        # 构建StringToSign
        string_to_sign = f"{method}\n{content_md5}\n{headers.get('Content-Type', '')}\n{date}\n{canonicalized_oss_headers}{canonicalized_resource}"
        
        # 计算签名
        signature = base64.b64encode(
            hmac.new(
                self.access_key_secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # 添加Authorization头
        headers['Authorization'] = f"OSS {self.access_key}:{signature}"
        
        return headers
    
    def upload(self, file: bytes, filename: str) -> UploadResponse:
        """
        上传图片到阿里云OSS
        
        Args:
            file: 图片文件二进制数据
            filename: 文件名（将作为OSS对象的key）
            
        Returns:
            UploadResponse: 上传响应对象
            
        Raises:
            UploadError: 上传失败时抛出异常
        """
        # 记录开始上传的日志
        self.logger.info(f"Starting OSS upload for file: {filename}, size: {len(file)} bytes")
        
        try:
            # 构建对象路径
            object_key = f"/{filename}"
            
            # 准备请求头
            headers = {
                'Content-Type': 'image/png',
                'x-oss-object-acl': 'public-read'  # 设置为公共读
            }
            
            # 签名请求
            signed_headers = self._sign_request('PUT', object_key, headers, file)
            
            # 构建完整URL
            upload_url = f"{self.base_url}{object_key}"
            self.logger.debug(f"OSS upload URL: {upload_url}")
            
            # 发送请求
            response = requests.put(
                upload_url,
                data=file,
                headers=signed_headers
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"OSS upload failed with status {response.status_code}, response: {response.text}"
                self.logger.error(f"OSS upload failed for {filename}: {error_msg}")
                raise UploadError(
                    message=f"OSS upload failed with status {response.status_code}",
                    error_type=UploadErrorType.SERVER_ERROR,
                    status_code=response.status_code,
                    details={'response': response.text}
                )
            
            # 构建访问URL
            if self.endpoint.startswith(('http://', 'https://')):
                access_url = f"{self.endpoint}/{self.bucket_name}{object_key}"
            else:
                access_url = f"https://{self.bucket_name}.{self.endpoint}{object_key}"
            
            # 构建图片元数据
            image_metadata = ImageMetadata(
                width=0,  # OSS PUT不返回图片尺寸
                height=0,
                filename=filename,
                size=len(file),
                url=access_url,
                delete_url=None  # OSS需要单独的删除操作
            )
            
            # 记录上传成功的日志
            self.logger.info(f"OSS upload successful for {filename}, URL: {access_url}")
            
            return UploadResponse(
                success=True,
                code="success",
                message="Upload to Aliyun OSS success",
                data=image_metadata
            )
            
        except requests.RequestException as e:
            error_msg = f"OSS upload request failed: {str(e)}"
            self.logger.error(f"OSS upload request failed for {filename}: {error_msg}")
            raise UploadError(
                message=error_msg,
                error_type=UploadErrorType.NETWORK_ERROR,
                original_error=e
            )
        except UploadError:
            # UploadError 已经被记录了，直接重新抛出
            raise
        except Exception as e:
            error_msg = f"OSS upload failed: {str(e)}"
            self.logger.error(f"OSS upload unexpected error for {filename}: {error_msg}")
            raise UploadError(
                message=error_msg,
                error_type=UploadErrorType.UNKNOWN,
                original_error=e
            )


class CloudFlareImgBedUploader(ImageUploader):
    """CloudFlare图床上传器"""

    def __init__(self, auth_code: str, api_url: str, upload_folder: str = ""):
        """
        初始化CloudFlare图床上传器
        
        Args:
            auth_code: 认证码
            api_url: 上传API地址
            upload_folder: 上传文件夹路径（可选）
        """
        self.auth_code = auth_code
        self.api_url = api_url
        self.upload_folder = upload_folder

    def upload(self, file: bytes, filename: str) -> UploadResponse:
        """
        上传图片到CloudFlare图床
        
        Args:
            file: 图片文件二进制数据
            filename: 文件名
            
        Returns:
            UploadResponse: 上传响应对象
            
        Raises:
            UploadError: 上传失败时抛出异常
        """
        try:
            # 准备请求URL参数
            params = []
            if self.upload_folder:
                params.append(f"uploadFolder={self.upload_folder}")
            if self.auth_code:
                params.append(f"authCode={self.auth_code}")
            params.append("uploadNameType=origin")

            request_url = f"{self.api_url}?{'&'.join(params)}"

            # 准备文件数据
            files = {
                "file": (filename, file)
            }
            
            # 发送请求
            response = requests.post(
                request_url,
                files=files
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 验证响应格式
            if not result or not isinstance(result, list) or len(result) == 0:
                raise UploadError(
                    message="Invalid response format",
                    error_type=UploadErrorType.PARSE_ERROR
                )
                
            # 获取文件URL
            file_path = result[0].get("src")
            if not file_path:
                raise UploadError(
                    message="Missing file URL in response",
                    error_type=UploadErrorType.PARSE_ERROR
                )
                
            # 构建完整URL（如果返回的是相对路径）
            base_url = self.api_url.split("/upload")[0]
            full_url = file_path if file_path.startswith(("http://", "https://")) else f"{base_url}{file_path}"
                
            # 构建图片元数据（注意：CloudFlare-ImgBed不返回所有元数据，所以部分字段为默认值）
            image_metadata = ImageMetadata(
                width=0,  # CloudFlare-ImgBed不返回宽度
                height=0,  # CloudFlare-ImgBed不返回高度
                filename=filename,
                size=0,  # CloudFlare-ImgBed不返回大小
                url=full_url,
                delete_url=None  # CloudFlare-ImgBed不返回删除URL
            )
            
            return UploadResponse(
                success=True,
                code="success",
                message="Upload success",
                data=image_metadata
            )
            
        except requests.RequestException as e:
            # 处理网络请求相关错误
            raise UploadError(
                message=f"Upload request failed: {str(e)}",
                error_type=UploadErrorType.NETWORK_ERROR,
                original_error=e
            )
        except (KeyError, ValueError, TypeError, IndexError) as e:
            # 处理响应解析错误
            raise UploadError(
                message=f"Invalid response format: {str(e)}",
                error_type=UploadErrorType.PARSE_ERROR,
                original_error=e
            )
        except UploadError:
            # 重新抛出已经是 UploadError 类型的异常
            raise
        except Exception as e:
            # 处理其他未预期的错误
            raise UploadError(
                message=f"Upload failed: {str(e)}",
                error_type=UploadErrorType.UNKNOWN,
                original_error=e
            )
    
class ImageUploaderFactory:
    @staticmethod
    def create(provider: str, **credentials) -> ImageUploader:
        if provider == "smms":
            return SmMsUploader(credentials["api_key"])
        elif provider == "qiniu":
            return QiniuUploader(
                credentials["access_key"], 
                credentials["secret_key"]
            )
        elif provider == "picgo":
            api_url = credentials.get("api_url") or "https://www.picgo.net/api/1/upload"
            return PicGoUploader(credentials["api_key"], api_url)
        elif provider == "cloudflare_imgbed":
            return CloudFlareImgBedUploader(
                credentials["auth_code"],
                credentials["base_url"],
                credentials.get("upload_folder", ""),
            )
        elif provider == "aliyun_oss":
            return AliyunOSSUploader(
                credentials["access_key"],
                credentials["access_key_secret"],
                credentials["bucket_name"],
                credentials["endpoint"],
                credentials["region"],
                credentials.get("use_internal", False)
            )
        raise ValueError(f"Unknown provider: {provider}")
