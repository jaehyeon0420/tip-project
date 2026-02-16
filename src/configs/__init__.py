import os
import yaml
from jinja2 import Template

_config_dir = os.path.dirname(os.path.abspath(__file__))

def _load_yaml(filename: str) -> dict:
    with open(os.path.join(_config_dir, filename), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

model_config: dict = _load_yaml('model_config.yaml')
_prompts_raw: dict = _load_yaml('prompts.yaml')

def get_system_prompt(task: str) -> str:
    """system 프롬프트 반환 (정적 텍스트, 렌더링 불필요)"""
    return _prompts_raw['prompts'][task]['system']

def render_system_prompt(task: str, **context) -> str:
    """system 프롬프트 템플릿을 context로 렌더링하여 반환"""
    template_str = _prompts_raw['prompts'][task]['system']
    template = Template(template_str)
    return template.render(**context)

def render_user_prompt(task: str, **context) -> str:
    """user 프롬프트 템플릿을 context로 렌더링하여 반환"""
    template_str = _prompts_raw['prompts'][task]['user']
    template = Template(template_str)
    return template.render(**context)
def get_user_prompt(task: str, **context) -> str:
    """user 프롬프트 반환 (정적 텍스트, 렌더링 불필요)"""
    return _prompts_raw['prompts'][task]['user']
def get_detail_prompt(task: str, **context) -> str:
    """detail 프롬프트 반환 (정적 텍스트, 렌더링 불필요)"""
    return _prompts_raw['prompts'][task]['detail']
