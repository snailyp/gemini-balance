import base64
import time
import uuid

from google import genai
from google.genai import types

from app.config.config import settings
from app.core.constants import VALID_IMAGE_RATIOS
from app.domain.openai_models import ImageGenerationRequest
from app.log.logger import get_image_create_logger
from app.utils.helpers import is_image_upload_configured
from app.utils.uploader import ImageUploaderFactory

logger = get_image_create_logger()


class ImageCreateService:
    def __init__(self, aspect_ratio="1:1"):
        self.image_model = settings.CREATE_IMAGE_MODEL
        self.aspect_ratio = aspect_ratio

    def parse_prompt_parameters(self, prompt: str) -> tuple:
        """从prompt中解析参数
        支持的格式:
        - {n:数量} 例如: {n:2} 生成2张图片
        - {ratio:比例} 例如: {ratio:16:9} 使用16:9比例
        """
        import re

        # 默认值
        n = 1
        aspect_ratio = self.aspect_ratio

        # 解析n参数
        n_match = re.search(r"{n:(\d+)}", prompt)
        if n_match:
            n = int(n_match.group(1))
            if n < 1 or n > 4:
                raise ValueError(f"Invalid n value: {n}. Must be between 1 and 4.")
            prompt = prompt.replace(n_match.group(0), "").strip()

        # 解析ratio参数
        ratio_match = re.search(r"{ratio:(\d+:\d+)}", prompt)
        if ratio_match:
            aspect_ratio = ratio_match.group(1)
            if aspect_ratio not in VALID_IMAGE_RATIOS:
                raise ValueError(
                    f"Invalid ratio: {aspect_ratio}. Must be one of: {', '.join(VALID_IMAGE_RATIOS)}"
                )
            prompt = prompt.replace(ratio_match.group(0), "").strip()

        return prompt, n, aspect_ratio

    def generate_images(self, request: ImageGenerationRequest):
        client = genai.Client(api_key=settings.PAID_KEY)

        if request.size == "1024x1024":
            self.aspect_ratio = "1:1"
        elif request.size == "1792x1024":
            self.aspect_ratio = "16:9"
        elif request.size == "1027x1792":
            self.aspect_ratio = "9:16"
        else:
            raise ValueError(
                f"Invalid size: {request.size}. Supported sizes are 1024x1024, 1792x1024, and 1024x1792."
            )

        # 解析prompt中的参数
        cleaned_prompt, prompt_n, prompt_ratio = self.parse_prompt_parameters(
            request.prompt
        )
        request.prompt = cleaned_prompt

        # 如果prompt中指定了n，则覆盖请求中的n
        if prompt_n > 1:
            request.n = prompt_n

        # 如果prompt中指定了ratio，则覆盖默认的aspect_ratio
        if prompt_ratio != self.aspect_ratio:
            self.aspect_ratio = prompt_ratio

        response = client.models.generate_images(
            model=self.image_model,
            prompt=request.prompt,
            config=types.GenerateImagesConfig(
                number_of_images=request.n,
                output_mime_type="image/png",
                aspect_ratio=self.aspect_ratio,
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
                person_generation="ALLOW_ADULT",
            ),
        )

        if response.generated_images:
            images_data = []
            for index, generated_image in enumerate(response.generated_images):
                image_data = generated_image.image.image_bytes
                image_uploader = None

                # Return base64 if explicitly requested or if no uploader is configured
                if (
                    request.response_format == "b64_json"
                    or not is_image_upload_configured(settings)
                ):
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    images_data.append(
                        {"b64_json": base64_image, "revised_prompt": request.prompt}
                    )
                    continue
                else:
                    # Upload to configured provider
                    current_date = time.strftime("%Y/%m/%d")
                    filename = f"{current_date}/{uuid.uuid4().hex[:8]}.png"

                    if settings.UPLOAD_PROVIDER == "smms":
                        image_uploader = ImageUploaderFactory.create(
                            provider=settings.UPLOAD_PROVIDER,
                            api_key=settings.SMMS_SECRET_TOKEN,
                        )
                    elif settings.UPLOAD_PROVIDER == "picgo":
                        image_uploader = ImageUploaderFactory.create(
                            provider=settings.UPLOAD_PROVIDER,
                            api_key=settings.PICGO_API_KEY,
                            api_url=settings.PICGO_API_URL,
                        )
                    elif settings.UPLOAD_PROVIDER == "cloudflare_imgbed":
                        image_uploader = ImageUploaderFactory.create(
                            provider=settings.UPLOAD_PROVIDER,
                            base_url=settings.CLOUDFLARE_IMGBED_URL,
                            auth_code=settings.CLOUDFLARE_IMGBED_AUTH_CODE,
                            upload_folder=settings.CLOUDFLARE_IMGBED_UPLOAD_FOLDER,
                        )
                    elif settings.UPLOAD_PROVIDER == "aliyun_oss":
                        image_uploader = ImageUploaderFactory.create(
                            provider=settings.UPLOAD_PROVIDER,
                            access_key=settings.OSS_ACCESS_KEY,
                            access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
                            bucket_name=settings.OSS_BUCKET_NAME,
                            endpoint=settings.OSS_ENDPOINT,
                            region=settings.OSS_REGION,
                            use_internal=False
                        )
                    else:
                        raise ValueError(
                            f"Unsupported upload provider: {settings.UPLOAD_PROVIDER}"
                        )

                    upload_response = image_uploader.upload(image_data, filename)

                    images_data.append(
                        {
                            "url": f"{upload_response.data.url}",
                            "revised_prompt": request.prompt,
                        }
                    )

            response_data = {
                "created": int(time.time()),
                "data": images_data,
            }
            return response_data
        else:
            raise Exception("I can't generate these images")

    def generate_images_chat(self, request: ImageGenerationRequest) -> str:
        response = self.generate_images(request)
        image_datas = response["data"]
        if image_datas:
            markdown_images = []
            for index, image_data in enumerate(image_datas):
                if "url" in image_data:
                    markdown_images.append(
                        f"![Generated Image {index+1}]({image_data['url']})"
                    )
                else:
                    # 如果是base64格式，创建data URL
                    markdown_images.append(
                        f"![Generated Image {index+1}](data:image/png;base64,{image_data['b64_json']})"
                    )
            return "\n".join(markdown_images)
