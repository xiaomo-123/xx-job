
# API调用模块，负责执行HTTP请求和处理响应

import json
import requests
import time
from jsonpath_ng import parse

class ApiClient:
    def __init__(self):
        self.timeout = 30  # 默认请求超时时间(秒)

    def execute_step(self, step, context=None):
        """
        执行API调用步骤

        参数:
            step: API步骤配置，包含url、method、headers、body等信息
            context: 上下文参数，用于替换URL和请求体中的占位符

        返回:
            {
                'success': bool,  # 是否成功
                'response': dict,  # 响应内容
                'status_code': int,  # HTTP状态码
                'error': str,  # 错误信息(如果有)
                'extracted_params': dict  # 提取的参数
            }
        """
        if context is None:
            context = {}

        result = {
            'success': False,
            'response': None,
            'status_code': None,
            'error': None,
            'extracted_params': {}
        }

        try:
            # 准备请求参数
            url = self._replace_placeholders(step.get('url', ''), context)
            method = step.get('method', 'GET').upper()

            # 获取原始的请求头和请求体，确保引用值被保留
            original_headers = step.get('headers', {})
            original_body = step.get('body', {})

            # 替换请求头和请求体中的占位符
            headers = self._replace_placeholders_dict(original_headers, context)
            body = self._replace_placeholders_dict(original_body, context)

            # 确保请求头和请求体的引用值被正确处理
            # 特别注意处理像 "Authorization": "Bearer ${token}" 这样的引用

            # 记录原始和替换后的请求信息，便于调试
            step_name = step.get('name', '未知')
            print(f"=== 步骤 {step_name} 请求信息 ===")
            print(f"上下文参数: {context}")
            print(f"原始请求头: {original_headers}")
            print(f"替换后请求头: {headers}")
            print(f"原始请求体: {original_body}")
            print(f"替换后请求体: {body}")

            # 检查关键参数是否被正确替换
            if 'Authorization' in headers:
                auth_value = headers.get('Authorization', '')
                # 检查标准格式 ${token}
                if '${token}' in auth_value:
                    if 'token' in context:
                        # 直接替换请求头中的token
                        headers['Authorization'] = auth_value.replace('${token}', str(context['token']))
                        print(f"✓ 成功替换token: {context['token']}")
                        # 验证token是否为空
                        if not context['token'] or (isinstance(context['token'], str) and not context['token'].strip()):
                            print("✗ 警告: token值为空")
                    else:
                        print("✗ 警告: 请求头中包含${token}但上下文中没有token参数")
                # 检查假设性格式 $token
                elif '$token' in auth_value and '${token}' not in auth_value:
                    if 'token' in context:
                        # 直接替换请求头中的token
                        headers['Authorization'] = auth_value.replace('$token', str(context['token']))
                        print(f"✓ 成功替换假设性token: {context['token']}")
                        # 验证token是否为空
                        if not context['token'] or (isinstance(context['token'], str) and not context['token'].strip()):
                            print("✗ 警告: token值为空")
                    else:
                        print("✗ 警告: 请求头中包含$token但上下文中没有token参数")

            # 检查其他可能的引用参数
            for key, value in headers.items():
                if isinstance(value, str) and '${' in value:
                    import re
                    placeholders = re.findall(r'\$\{([^}]+)\}', value)
                    for placeholder in placeholders:
                        if placeholder in context:
                            print(f"✓ 请求头 {key} 成功替换参数 {placeholder}: {context[placeholder]}")
                            # 验证参数是否为空
                            if not context[placeholder] or (isinstance(context[placeholder], str) and not context[placeholder].strip()):
                                print(f"✗ 警告: 参数 {placeholder} 值为空")
                        else:
                            print(f"✗ 警告: 请求头 {key} 包含参数 {placeholder} 但上下文中没有该参数")

            # 检查请求体中的引用参数
            if isinstance(body, dict):
                for key, value in body.items():
                    if isinstance(value, str):
                        # 检查标准格式 ${param}
                        if '${' in value:
                            import re
                            placeholders = re.findall(r'\$\{([^}]+)\}', value)
                            for placeholder in placeholders:
                                if placeholder in context:
                                    print(f"✓ 请求体 {key} 成功替换参数 {placeholder}: {context[placeholder]}")
                                    # 验证参数是否为空
                                    if not context[placeholder] or (isinstance(context[placeholder], str) and not context[placeholder].strip()):
                                        print(f"✗ 警告: 参数 {placeholder} 值为空")
                                else:
                                    print(f"✗ 警告: 请求体 {key} 包含参数 {placeholder} 但上下文中没有该参数")

                        # 检查假设性格式 $param (但不是 ${param})
                        elif '$' in value and '${' not in value:
                            import re
                            simple_placeholders = re.findall(r'\$(\w+)', value)
                            for placeholder in simple_placeholders:
                                if placeholder in context:
                                    print(f"✓ 请求体 {key} 成功替换假设性参数 {placeholder}: {context[placeholder]}")
                                    # 验证参数是否为空
                                    if not context[placeholder] or (isinstance(context[placeholder], str) and not context[placeholder].strip()):
                                        print(f"✗ 警告: 参数 {placeholder} 值为空")
                                else:
                                    print(f"✗ 警告: 请求体 {key} 包含假设性参数 {placeholder} 但上下文中没有该参数")

            # 无论是否成功，先记录请求信息
            result['url'] = url
            result['method'] = method
            result['headers'] = headers
            result['body'] = body

            # 发送请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ['POST', 'PUT', 'PATCH'] else None,
                params=body if method == 'GET' else None,
                timeout=self.timeout
            )

            result['status_code'] = response.status_code
            result['response'] = response.json() if response.headers.get('content-type', '').find('application/json') != -1 else response.text

            # 检查响应状态
            if response.status_code >= 200 and response.status_code < 300:
                result['success'] = True

                # 提取参数
                if 'extract_params' in step and step['extract_params']:
                    result['extracted_params'] = self._extract_params(
                        result['response'], 
                        step['extract_params']
                    )
            else:
                result['error'] = f"HTTP错误: {response.status_code} - {response.text}"

        except requests.exceptions.Timeout:
            result['error'] = "请求超时"
        except requests.exceptions.ConnectionError:
            result['error'] = "连接错误"
        except json.JSONDecodeError:
            result['error'] = "响应不是有效的JSON格式"
        except Exception as e:
            result['error'] = f"未知错误: {str(e)}"

        return result

    def execute_chain(self, steps, retry_times=1):
        """
        执行API调用链

        参数:
            steps: API步骤列表
            retry_times: 失败重试次数

        返回:
            {
                'success': bool,  # 整个链是否成功
                'steps': list,  # 每个步骤的执行结果
                'error': str  # 错误信息(如果有)
            }
        """
        result = {
            'success': False,
            'steps': [],
            'error': None
        }

        context = {}  # 用于存储步骤间传递的参数

        for i, step in enumerate(steps):
            step_result = None
            retry_count = 0

            # 执行当前步骤，支持重试
            while retry_count <= retry_times:
                step_result = self.execute_step(step, context)

                if step_result['success']:
                    break

                retry_count += 1
                if retry_count <= retry_times:
                    time.sleep(1)  # 重试前等待1秒

            # 保存步骤结果
            result['steps'].append({
                'step_index': i,
                'step_name': step.get('name', f'步骤{i+1}'),
                'result': step_result
            })

            # 如果步骤失败，终止链式调用
            if not step_result['success']:
                result['error'] = f"步骤{i+1}失败: {step_result['error']}"
                return result

            # 将提取的参数添加到上下文中
            # 确保步骤之间的参数传递正确
            extracted_params = step_result['extracted_params']
            context.update(extracted_params)

            # 记录步骤执行结果，便于调试
            print(f"步骤 {i+1} ({step.get('name', '未知步骤')}) 执行完成")
            print(f"提取的参数: {extracted_params}")
            print(f"当前上下文: {context}")

            # 验证关键参数是否正确提取
            extract_params = step.get('extract_params', [])
            if extract_params:
                for param_config in extract_params:
                    param_name = param_config.get('name', '')
                    if param_name and param_name in context:
                        print(f"✓ 成功提取参数 {param_name}: {context[param_name]}")
                    elif param_name:
                        print(f"✗ 警告: 参数 {param_name} 未在响应中找到")

                # 特别检查token参数，因为它是链式调用的关键
                if i == 0 and any(p.get('name') == 'token' for p in extract_params):
                    if 'token' in context:
                        print(f"✓ 步骤 {i+1} 成功提取token，可用于后续步骤")
                    else:
                        print(f"✗ 警告: 步骤 {i+1} 应提取token参数但未找到，后续步骤可能失败")

            # 检查下一步是否需要当前步骤提取的参数
            if i < len(steps) - 1:
                next_step = steps[i+1]
                next_headers = next_step.get('headers', {})
                next_body = next_step.get('body', {})
                next_url = next_step.get('url', '')

                print(f"=== 检查步骤 {i+2} 的参数依赖 ===")

                # 检查下一步的请求头、请求体和URL中是否有占位符
                all_placeholders = set()
                placeholder_details = {}  # 记录占位符的详细信息

                # 从请求头中提取占位符
                for key, value in next_headers.items():
                    if isinstance(value, str):
                        import re
                        # 检查标准格式 ${param}
                        if '${' in value:
                            placeholders = re.findall(r'\$\{([^}]+)\}', value)
                            for placeholder in placeholders:
                                all_placeholders.add(placeholder)
                                if placeholder not in placeholder_details:
                                    placeholder_details[placeholder] = []
                                placeholder_details[placeholder].append(f"请求头 {key}")

                        # 检查假设性格式 $param (但不是 ${param})
                        elif '$' in value and '${' not in value:
                            # 特别检查 {"Authorization":$token} 格式
                            if key == 'Authorization' and '$token' in value:
                                all_placeholders.add('token')
                                if 'token' not in placeholder_details:
                                    placeholder_details['token'] = []
                                placeholder_details['token'].append(f"请求头 {key} (假设性格式)")
                            else:
                                simple_placeholders = re.findall(r'\$(\w+)', value)
                                for placeholder in simple_placeholders:
                                    all_placeholders.add(placeholder)
                                    if placeholder not in placeholder_details:
                                        placeholder_details[placeholder] = []
                                    placeholder_details[placeholder].append(f"请求头 {key} (假设性格式)")

                # 从请求体中提取占位符
                if isinstance(next_body, dict):
                    for key, value in next_body.items():
                        if isinstance(value, str):
                            import re
                            # 检查标准格式 ${param}
                            if '${' in value:
                                placeholders = re.findall(r'\$\{([^}]+)\}', value)
                                for placeholder in placeholders:
                                    all_placeholders.add(placeholder)
                                    if placeholder not in placeholder_details:
                                        placeholder_details[placeholder] = []
                                    placeholder_details[placeholder].append(f"请求体 {key}")

                            # 检查假设性格式 $param (但不是 ${param})
                            elif '$' in value and '${' not in value:
                                # 特别检查 {"name":$name} 格式
                                if key == 'name' and '$name' in value:
                                    all_placeholders.add('name')
                                    if 'name' not in placeholder_details:
                                        placeholder_details['name'] = []
                                    placeholder_details['name'].append(f"请求体 {key} (假设性格式)")
                                else:
                                    simple_placeholders = re.findall(r'\$(\w+)', value)
                                    for placeholder in simple_placeholders:
                                        all_placeholders.add(placeholder)
                                        if placeholder not in placeholder_details:
                                            placeholder_details[placeholder] = []
                                        placeholder_details[placeholder].append(f"请求体 {key} (假设性格式)")

                # 从URL中提取占位符
                if isinstance(next_url, str):
                    import re
                    # 检查标准格式 ${param}
                    if '${' in next_url:
                        placeholders = re.findall(r'\$\{([^}]+)\}', next_url)
                        for placeholder in placeholders:
                            all_placeholders.add(placeholder)
                            if placeholder not in placeholder_details:
                                placeholder_details[placeholder] = []
                            placeholder_details[placeholder].append("URL")

                    # 检查假设性格式 $param (但不是 ${param})
                    elif '$' in next_url and '${' not in next_url:
                        simple_placeholders = re.findall(r'\$(\w+)', next_url)
                        for placeholder in simple_placeholders:
                            all_placeholders.add(placeholder)
                            if placeholder not in placeholder_details:
                                placeholder_details[placeholder] = []
                            placeholder_details[placeholder].append("URL (假设性格式)")

                # 检查所有占位符是否在上下文中
                for placeholder in all_placeholders:
                    locations = ", ".join(placeholder_details[placeholder])
                    if placeholder in context:
                        value = context[placeholder]
                        print(f"✓ 下一步需要参数 {placeholder} (使用于: {locations})，已在上下文中找到，值: {value}")

                        # 验证参数是否为空
                        if not value or (isinstance(value, str) and not value.strip()):
                            print(f"✗ 警告: 参数 {placeholder} 值为空")
                    else:
                        print(f"✗ 警告: 下一步需要参数 {placeholder} (使用于: {locations})，但未在上下文中找到")

                        # 检查是否在当前步骤的extract_params中配置了提取
                        extract_params = step.get('extract_params', [])
                        if any(p.get('name') == placeholder for p in extract_params):
                            print(f"✗ 错误: 参数 {placeholder} 已在当前步骤的extract_params中配置，但未能成功提取")
                        else:
                            print(f"✗ 提示: 参数 {placeholder} 未在当前步骤的extract_params中配置，请检查配置")

        # 所有步骤都成功
        result['success'] = True
        return result

    def _replace_placeholders_dict(self, data, context):
        """递归替换字典中的所有占位符"""
        if isinstance(data, dict):
            # 特殊处理Authorization请求头，确保token直接替换
            result = {}
            for k, v in data.items():
                if k == 'Authorization' and isinstance(v, str):
                    # 直接替换token，不通过递归处理
                    if '${token}' in v and 'token' in context:
                        result[k] = v.replace('${token}', str(context['token']))
                    elif '$token' in v and '${token}' not in v and 'token' in context:
                        result[k] = v.replace('$token', str(context['token']))
                    else:
                        result[k] = self._replace_placeholders_dict(v, context)
                else:
                    result[k] = self._replace_placeholders_dict(v, context)
            return result
        elif isinstance(data, list):
            return [self._replace_placeholders_dict(item, context) for item in data]
        elif isinstance(data, str):
            return self._replace_placeholders(data, context)
        else:
            return data

    def _replace_placeholders(self, text, context):
        """替换文本中的占位符，格式为 ${param_name}"""
        if not text or not isinstance(text, str):
            return text

        # 递归替换，直到没有占位符为止
        max_iterations = 10  # 防止无限循环
        original_text = text  # 保存原始文本用于日志

        # 特殊处理：检查是否是假设性参数格式
        # 例如 {"Authorization":$token} 或 {"name":$name}
        import re
        json_pattern = r'(\{[^}]*\$(\w+)[^}]*\})'
        json_matches = re.findall(json_pattern, text)

        # 检查假设性参数格式
        for full_match, param_name in json_matches:
            if param_name in context:
                print(f"✓ 找到假设性参数 ${param_name} 在上下文中，值: {context[param_name]}")
            else:
                print(f"✗ 警告: 假设性参数 ${param_name} 不在上下文中")

        # 提取所有占位符，确保它们在上下文中
        placeholders = re.findall(r'\$\{([^}]+)\}', text)

        # 检查所有占位符是否在上下文中
        for placeholder in placeholders:
            if placeholder in context:
                print(f"✓ 找到占位符 ${placeholder} 在上下文中，值: {context[placeholder]}")
            else:
                print(f"✗ 警告: 占位符 ${placeholder} 不在上下文中")

        for iteration in range(max_iterations):
            new_text = text
            for key, value in context.items():
                # 处理标准格式 ${param_name}
                placeholder = f'${{{key}}}'
                if placeholder in new_text:
                    new_text = new_text.replace(placeholder, str(value))
                    print(f"替换占位符 {placeholder} -> {value}")

                # 处理假设性参数格式 $param_name
                placeholder_simple = f'${key}'
                if placeholder_simple in new_text and f'${{{key}}}' not in new_text:
                    # 只在JSON字符串中替换简单格式，避免误替换
                    if re.search(r'[\"\']\s*\$' + key + r'\s*[\"\']', new_text) or re.search(r':\s*\$' + key, new_text):
                        new_text = new_text.replace(placeholder_simple, str(value))
                        print(f"替换假设性参数 {placeholder_simple} -> {value}")

            # 如果没有变化，说明已经没有占位符了
            if new_text == text:
                break

            text = new_text

        # 记录替换结果
        if original_text != text:
            print(f"占位符替换结果: {original_text} -> {text}")

        # 再次检查是否还有未替换的占位符
        remaining_placeholders = re.findall(r'\$\{([^}]+)\}', text)
        if remaining_placeholders:
            print(f"警告: 仍有未替换的占位符: {remaining_placeholders}")

        # 检查是否还有未替换的假设性参数
        remaining_simple_placeholders = re.findall(r'\$(\w+)(?![^{])', text)
        if remaining_simple_placeholders:
            print(f"警告: 仍有未替换的假设性参数: {remaining_simple_placeholders}")

        return text

    def _extract_params(self, response, extract_params):
        """
        从响应中提取参数

        参数:
            response: API响应
            extract_params: 提取参数配置，格式为:
                [
                    {
                        'name': '参数名',
                        'path': 'JSON路径，如 $.data.id',
                        'type': '参数类型，如 string, number, boolean'
                    },
                    ...
                ]

        返回:
            提取的参数字典
        """
        extracted = {}
        print(f"=== 提取参数 ===")
        print(f"响应数据: {response}")

        for param in extract_params:
            name = param.get('name')
            path = param.get('path')
            param_type = param.get('type', 'string')

            if not name or not path:
                print(f"警告: 参数配置不完整，跳过: {param}")
                continue

            print(f"尝试提取参数: name={name}, path={path}, type={param_type}")

            try:
                # 处理特殊路径格式，如 $data.token 转换为 $.data.token
                if path.startswith('$') and not path.startswith('$.'):
                    path = '$.' + path[1:]  # 在$后添加.
                    print(f"转换路径格式: {path}")

                # 使用jsonpath_ng解析JSON路径
                jsonpath_expr = parse(path)
                matches = jsonpath_expr.find(response)

                if matches:
                    value = matches[0].value
                    print(f"找到匹配值: {value}")

                    # 类型转换
                    if param_type == 'number':
                        try:
                            value = float(value) if '.' in str(value) else int(value)
                            print(f"转换为数字类型: {value}")
                        except ValueError:
                            print(f"警告: 无法将值 {value} 转换为数字类型")
                            continue
                    elif param_type == 'boolean':
                        if isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                            print(f"转换为布尔类型: {value}")

                    # 验证提取的值是否为空
                    if value is None or (isinstance(value, str) and not value.strip()):
                        print(f"警告: 参数 {name} 的值为空")
                        continue

                    extracted[name] = value
                    print(f"✓ 成功提取参数 {name}: {value} (类型: {type(value).__name__})")
                else:
                    print(f"✗ 警告: 路径 {path} 在响应中未找到匹配项")
            except Exception as e:
                # 提取参数失败，记录错误但继续处理其他参数
                print(f"✗ 提取参数 {name} 失败: {str(e)}")

        print(f"提取的所有参数: {extracted}")
        return extracted
