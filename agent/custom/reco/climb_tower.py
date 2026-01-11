from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import json


@AgentServer.custom_recognition("shop_recognition")
class ShopRecognition(CustomRecognition):
    """商店识别器 - 简化版，仅用于触发动作"""
    
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        """简化的商店识别，直接返回成功，让动作器处理所有逻辑"""
        
        config = argv.custom_recognition_param
        print(f"商店识别器参数: {config}")
        
        try:
            # 如果 config 是字符串，尝试解析为 JSON 对象
            if isinstance(config, str):
                shop_config = json.loads(config)
            else:
                shop_config = config
            
            shop_type = shop_config.get("shop_type", "regular")
            print(f"商店类型: {shop_type}")
            
            # 简化识别逻辑，直接返回成功，让动作器处理所有状态识别和逻辑
            # 这样可以保持JSON配置不变，同时让动作器独立运行
            return CustomRecognition.AnalyzeResult(
                box=[0, 0, 10, 10],  # 返回一个默认的box，表示识别成功
                detail=json.dumps({
                    "current_state": "ready",
                    "shop_type": shop_type
                })
            )
            
        except Exception as e:
            print(f"商店识别器错误: {e}")
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail=f"Error: {str(e)}",
            )
