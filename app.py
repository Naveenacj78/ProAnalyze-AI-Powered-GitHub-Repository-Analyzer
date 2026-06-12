"""
ProAnalyze - Python Version
A comprehensive GitHub repository analysis tool with AI-powered insights and visualizations.
"""

import os
import re
import base64
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import streamlit as st
import requests
import html
from github import Github
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
class Config:
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    MODEL_URL = "https://api.together.xyz/v1/chat/completions"
    MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    REWRITER_MODEL = os.getenv("REWRITER_MODEL", "meta-llama/Llama-3-8b-instruct")
    MAX_TOKENS = 4096
    MAX_FILES = 5
    MAX_FILE_SIZE = 2000
    MAX_RETRIES = 3
    BASE_DELAY = 2

# Data Models
class FileData(BaseModel):
    name: str
    path: str
    content: str
    size: int

class RepositoryData(BaseModel):
    name: str
    description: str
    language: str
    stars: int
    forks: int
    files: List[FileData]
    analysis: Optional[str] = None

class WorkflowStep(BaseModel):
    id: str
    title: str
    description: str
    is_system: bool

class WorkflowDiagrams(BaseModel):
    system: str
    user: str

# GitHub Service
class GitHubService:
    def __init__(self, token: str):
        self.github = Github(token)
    
    def parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse various GitHub URL formats and return (owner, repo).

        Accepts examples:
        - https://github.com/owner/repo
        - http://github.com/owner/repo/
        - github.com/owner/repo.git
        - owner/repo
        - https://github.com/owner/repo/tree/main (extra path ignored)
        """
        candidate = url.strip()

        # If it's a plain owner/repo format
        if re.fullmatch(r"[^/]+/[^/]+", candidate):
            owner, repo = candidate.split("/", 1)
        else:
            # Ensure it has a scheme so urlparse works consistently
            if not re.match(r"^https?://", candidate, flags=re.IGNORECASE):
                candidate = "https://" + candidate
            parsed = urlparse(candidate)
            host_path = (parsed.netloc + parsed.path).lstrip("/")
            parts = [p for p in host_path.split("/") if p]
            # Find the first occurrence of 'github.com' and take next two segments
            if parts and parts[0].lower() == "github.com":
                parts = parts[1:]
            if len(parts) < 2:
                raise ValueError("Invalid GitHub URL")
            owner, repo = parts[0], parts[1]

        # Normalize repo (strip .git and trailing slashes)
        repo = re.sub(r"\.git$", "", repo, flags=re.IGNORECASE).strip("/")
        owner = owner.strip("/")

        if not owner or not repo:
            raise ValueError("Invalid GitHub URL")
        return owner, repo
    
    async def fetch_repository_data(self, owner: str, repo: str) -> RepositoryData:
        """Fetch repository data and files from GitHub."""
        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            
            # Get repository info
            repo_data = {
                'name': repo_obj.name,
                'description': repo_obj.description or '',
                'language': repo_obj.language or 'Unknown',
                'stars': repo_obj.stargazers_count,
                'forks': repo_obj.forks_count,
                'files': []
            }
            
            # Fetch files recursively
            files = await self._fetch_files_recursive(repo_obj, '')
            repo_data['files'] = files
            
            return RepositoryData(**repo_data)
            
        except Exception as e:
            raise Exception(f"Failed to fetch repository data: {str(e)}")
    
    async def _fetch_files_recursive(self, repo, path: str) -> List[FileData]:
        """Recursively fetch files from repository."""
        files = []
        try:
            contents = repo.get_contents(path)
            
            for item in contents:
                if item.type == 'file':
                    # Only fetch Python files
                    if item.name.endswith(('.py', '.ipynb')):
                        try:
                            content = base64.b64decode(item.content).decode('utf-8')
                            files.append(FileData(
                                name=item.name,
                                path=item.path,
                                content=content,
                                size=item.size
                            ))
                        except Exception as e:
                            print(f"Error reading file {item.path}: {e}")
                            continue
                elif item.type == 'dir':
                    # Recursively fetch from subdirectories
                    sub_files = await self._fetch_files_recursive(repo, item.path)
                    files.extend(sub_files)
                    
        except Exception as e:
            print(f"Error fetching contents from {path}: {e}")
            
        return files

# Analysis Service
class AnalysisService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.config = Config()
    
    def _is_python_file(self, filename: str) -> bool:
        """Check if file is a Python file."""
        return filename.lower().endswith(('.py', '.ipynb'))
    
    def _truncate_content(self, content: str) -> str:
        """Truncate content to max size."""
        if len(content) <= self.config.MAX_FILE_SIZE:
            return content
        return content[:self.config.MAX_FILE_SIZE] + '\n... (truncated)'
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by removing sensitive information."""
        content = re.sub(r'import os[\s\S]*?os\.environ', 'import os # Environment handling', content)
        content = re.sub(r'api_key\s*=\s*["\'][^"\']*["\']', 'api_key = "***"', content)
        content = re.sub(r'password\s*=\s*["\'][^"\']*["\']', 'password = "***"', content)
        content = re.sub(r'secret\s*=\s*["\'][^"\']*["\']', 'secret = "***"', content)
        return content
    
    def _generate_analysis_prompt(self, files: List[FileData]) -> str:
        """Generate analysis prompt for the LLM."""
        python_files = [
            f for f in files 
            if self._is_python_file(f.name)
        ][:self.config.MAX_FILES]
        
        if not python_files:
            return 'No Python files found in this repository.'
        
        files_summary = '\n\n'.join([
            f"### {file.name}\n```python\n{self._sanitize_content(self._truncate_content(file.content))}\n```"
            for file in python_files
        ])
        
        return f"""<s>[INST] You are a senior code analysis expert. Analyze these Python files and provide a comprehensive technical summary.

Files to analyze:

{files_summary}

You MUST provide a detailed analysis in this exact format, ensuring ALL sections are complete with substantial information:

## Project Overview
[Write 2-3 detailed paragraphs explaining:
- The main purpose and goals of the project
- The core methodology and approach used
- The problem it solves and its significance
Be specific about the project's role and impact.]

## Key Features
[List at least 6-8 main features, with each feature having 2-3 lines of explanation:
- Feature 1: Detailed description of what it does and how it benefits users
- Feature 2: Detailed description of what it does and how it benefits users
(continue with all features)
Focus on user-facing functionality and technical capabilities.]

## Libraries & Dependencies
[List ALL important libraries (at least 5-6) with 2-3 lines about their role:
- Library 1: Detailed explanation of how it's used in the project and why it's essential
- Library 2: Detailed explanation of how it's used in the project and why it's essential
(continue with all libraries)
Include both direct and indirect dependencies that are crucial.]

## Project Workflow
[CRITICAL: Provide a detailed, step-by-step explanation of how the project works from start to finish:
1. Initial Setup: How the system is initialized and configured
2. User Input: How users interact with the system and what inputs they provide
3. Processing Flow: How the system processes the inputs and what happens internally
4. Data Handling: How data flows through different components
5. Output Generation: How results are calculated and presented
6. Error Handling: How the system manages errors and edge cases

Each step MUST have 2-3 lines of detailed explanation.
Focus on the actual user journey and system operation flow.]

## Implementation Details
[List at least 6-7 key technical aspects with detailed explanations:
- Implementation 1: Detailed explanation of the technical approach and why it was chosen
- Implementation 2: Detailed explanation of the technical approach and why it was chosen
(continue with all implementations)
Include architecture decisions, design patterns, and technical solutions.]

## Project Strengths
[CRITICAL: List at least 5-6 major strengths with detailed explanations:
- Strength 1: Detailed explanation of why this is a strength and its impact
- Strength 2: Detailed explanation of why this is a strength and its impact
(continue with all strengths)
Focus on technical excellence, user benefits, and project advantages.]

## Areas for Improvement
[CRITICAL: List at least 4-5 specific suggestions for enhancement:
- Improvement 1: Detailed suggestion for future enhancement or expansion
- Improvement 2: Detailed suggestion for future enhancement or expansion
(continue with all improvements)
Focus ONLY on concrete improvement opportunities and future enhancements.
Each suggestion MUST include both what to improve and how to improve it.]

CRITICAL REQUIREMENTS:
1. ALL sections MUST be completed with the minimum number of points specified
2. Each point MUST have at least 2-3 lines of detailed explanation
3. The Project Workflow MUST describe the actual step-by-step operation flow
4. Project Strengths MUST highlight unique advantages and capabilities
5. Areas for Improvement MUST focus on concrete enhancement opportunities
6. Use technical language but ensure explanations are clear and specific
7. DO NOT skip or leave any section empty[/INST]</s>"""
    
    async def _make_analysis_request(self, prompt: str, attempt: int) -> Optional[str]:
        """Make analysis request to Together AI API."""
        try:
            print(f"Attempting analysis with Mixtral (attempt {attempt})")
            
            response = requests.post(
                self.config.MODEL_URL,
                json={
                    "model": self.config.MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": self.config.MAX_TOKENS,
                    "temperature": 0.3,
                    "top_p": 0.9
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message', {}).get('content'):
                    analysis = data['choices'][0]['message']['content'].strip()
                    
                    if len(analysis) < 50:
                        print('Response too short, retrying...')
                        return None
                    
                    formatted_analysis = self._format_analysis(analysis)
                    if not formatted_analysis:
                        print('Critical sections missing, retrying...')
                        return None
                    
                    return formatted_analysis
            
            print(f'Invalid response format: {response.text}')
            return None
            
        except requests.exceptions.RequestException as e:
            print(f'Analysis request failed: {e}')
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    raise Exception('Invalid Together AI API key. Please check your configuration.')
                elif e.response.status_code in [429, 503]:
                    delay = self.config.BASE_DELAY * (2 ** (attempt - 1))
                    print(f'Rate limit or service unavailable, waiting {delay}s...')
                    await asyncio.sleep(delay)
                    return None
            
            raise Exception(f'API request failed: {str(e)}')
    
    def _format_analysis(self, analysis: str) -> str:
        """Format and validate analysis response."""
        # Remove HTML tags
        analysis = re.sub(r'<[^>]+>', '', analysis)
        
        sections = [
            'Project Overview',
            'Key Features', 
            'Libraries & Dependencies',
            'Project Workflow',
            'Implementation Details',
            'Project Strengths',
            'Areas for Improvement'
        ]
        
        formatted = analysis.strip()
        formatted = re.sub(r'^(system|assistant|user):\s*', '', formatted, flags=re.MULTILINE).strip()
        
        # Check for critical sections
        critical_sections = ['Project Workflow', 'Project Strengths', 'Areas for Improvement']
        missing_critical = any(
            not re.search(f'## {section}\\n([\\s\\S]*?)(?=## |$)', formatted)
            for section in critical_sections
        )
        
        if missing_critical:
            print('Critical sections missing, retrying...')
            return ''
        
        return formatted
    
    async def analyze_code(self, files: List[FileData]) -> str:
        """Analyze code files using Mixtral 8x7B."""
        print('Starting code analysis...')
        prompt = self._generate_analysis_prompt(files)
        
        if prompt == 'No Python files found in this repository.':
            return """# Project Analysis

This repository does not contain any Python files (.py or .ipynb). Please try analyzing a Python project."""
        
        print(f'Found Python files to analyze. Prompt length: {len(prompt)}')
        
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                analysis = await self._make_analysis_request(prompt, attempt)
                
                if analysis:
                    return f"# Python Project Analysis\n\n{analysis}"
                
                if attempt == self.config.MAX_RETRIES:
                    raise Exception('Analysis failed after multiple attempts. The model response was invalid.')
                    
            except Exception as e:
                print(f'Attempt {attempt} failed: {e}')
                if attempt == self.config.MAX_RETRIES:
                    raise e
        
        raise Exception('Analysis failed after multiple attempts. Please try again later.')

# Workflow Diagram Service
class WorkflowDiagramService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.config = Config()
    
    async def _extract_workflow_steps_with_ai(self, workflow_text: str, files: Optional[List[FileData]] = None) -> List[WorkflowStep]:
        """Extract workflow steps using AI, leveraging repo files when available, with robust parsing and fallbacks."""
        try:
            # Prepare condensed code context from key files
            code_context = ""
            if files:
                sample = files[:6]
                parts = []
                for f in sample:
                    content = (f.content or "")
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    parts.append(f"### {f.path}\n```\n{content}\n```")
                code_context = "\n\n".join(parts)

            prompt = f"""<s>[INST] You are a senior software architect. Analyze the repository context and provide TWO detailed, step-by-step workflows:

CONTEXT FILES (for ground truth):
{code_context if code_context else '(no files provided)'}

WORKFLOW SECTION (if any):
{workflow_text or '(none)'}

Return ONLY a JSON object with this exact shape (no prose, no markdown, no fences):
{{
  "systemSteps": [
    {{"title": "specific internal action", "description": "what the system does, inputs/outputs, components involved"}},
    ... at least 8 concrete steps ...
  ],
  "userSteps": [
    {{"title": "specific user action", "description": "what user does and visible system response"}},
    ... at least 8 concrete steps ...
  ]
}}

Rules:
- Derive steps from actual code when possible (files above). Name components/APIs if identifiable.
- Focus systemSteps on data flow, validations, API calls (GitHub, LLM), processing, diagram generation.
- Focus userSteps on UI actions: entering repo URL, analysis, diagram generation, chat interactions.
- Ensure sequential, non-generic steps that match this project’s architecture.[/INST]</s>"""

            response = requests.post(
                self.config.MODEL_URL,
                json={
                    "model": self.config.MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1800,
                    "temperature": 0.2,
                    "top_p": 0.9
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )

            content = None
            if response.status_code == 200:
                content = response.json().get('choices', [{}])[0].get('message', {}).get('content')
            if not content:
                return self._infer_workflow_steps_from_text(workflow_text)

            import json
            obj_match = re.search(r"\{[\s\S]*\}", content)
            raw_obj = obj_match.group(0) if obj_match else None
            if raw_obj:
                try:
                    parsed_obj = json.loads(raw_obj)
                    sys_arr = parsed_obj.get('systemSteps')
                    usr_arr = parsed_obj.get('userSteps')
                    if isinstance(sys_arr, list) and isinstance(usr_arr, list):
                        steps: List[WorkflowStep] = []
                        for i, st in enumerate(sys_arr):
                            steps.append(WorkflowStep(
                                id=f"sys{i+1}",
                                title=str(st.get('title', '')).strip(),
                                description=str(st.get('description', '')).strip(),
                                is_system=True
                            ))
                        for i, st in enumerate(usr_arr):
                            steps.append(WorkflowStep(
                                id=f"user{i+1}",
                                title=str(st.get('title', '')).strip(),
                                description=str(st.get('description', '')).strip(),
                                is_system=False
                            ))
                        if steps:
                            return steps
                except Exception:
                    pass

            # Fallback: array of steps with isSystem
            arr_match = re.search(r"\[[\s\S]*\]", content)
            if arr_match:
                try:
                    parsed_steps = json.loads(arr_match.group(0))
                    steps = [
                        WorkflowStep(
                            id=f"step{i+1}",
                            title=str(st.get('title', '')).strip(),
                            description=str(st.get('description', '')).strip(),
                            is_system=bool(st.get('isSystem'))
                        ) for i, st in enumerate(parsed_steps)
                    ]
                    if steps:
                        return steps
                except Exception:
                    pass

            return self._infer_workflow_steps_from_text(workflow_text)

        except Exception as e:
            print(f'Error in extractWorkflowStepsWithAI: {e}')
            return self._infer_workflow_steps_from_text(workflow_text)

    def _infer_workflow_steps_from_text(self, workflow_text: str) -> List[WorkflowStep]:
        lines = [ln.strip(" -\t") for ln in (workflow_text or '').splitlines()]
        lines = [ln for ln in lines if ln]
        items: List[str] = []
        for ln in lines:
            m = re.match(r'(?:\d+\.|[-*])\s*(.+)', ln)
            items.append(m.group(1).strip() if m else ln)
        def mk(title: str, idx: int, is_system: bool) -> WorkflowStep:
            short = title[:120]
            return WorkflowStep(id=f"{'sys' if is_system else 'user'}{idx+1}", title=short, description="", is_system=is_system)
        half = max(4, min(8, len(items)//2)) if items else 6
        sys_items = (items[:half] or ['Initialize configuration','Validate inputs','Process core logic','Persist or prepare outputs','Format results','Handle errors'])
        user_items = (items[half:half*2] or ['Open app','Provide inputs','Start analysis','Wait for processing','View results','Follow suggestions'])
        steps: List[WorkflowStep] = []
        for i, t in enumerate(sys_items[:8]):
            steps.append(mk(t, i, True))
        for i, t in enumerate(user_items[:8]):
            steps.append(mk(t, i, False))
        return steps

    def _sanitize_dot_label(self, text: str) -> str:
        t = (text or "").replace("\\", "\\\\").replace("\"", "\\\"")
        t = re.sub(r"[\[\]\{\}]", "(", t)
        return t

    def _generate_diagram(self, steps: List[WorkflowStep]) -> str:
        """Generate a single-flow Graphviz DOT for the provided steps (system OR user)."""
        try:
            def sort_key(s: WorkflowStep):
                m = re.search(r'(\d+)$', s.id)
                return int(m.group(1)) if m else 9999
            ordered = sorted(steps, key=sort_key)

            lines = [
                "digraph Workflow {",
                "  rankdir=TB;",
                "  splines=ortho;",
                "  nodesep=1.0;",
                "  ranksep=1.2;",
                "  fontname=\"Arial\";",
                "  node [shape=box, style=filled, fillcolor=\"#ffffff\", color=\"#2563eb\", fontcolor=\"#0f172a\", fontname=\"Arial\", fontsize=13, margin=\"0.3,0.15\"];",
                "  edge [color=\"#64748b\", penwidth=1.4, arrowsize=0.9];",
            ]
            for idx, step in enumerate(ordered, start=1):
                title = self._sanitize_dot_label(step.title or f"Step {idx}")
                desc = self._sanitize_dot_label(step.description or "")
                label = f"{idx}. {title}" + ("\\n" + desc if desc else "")
                lines.append(f"  \"{step.id}\" [label=\"{label}\"];")
            for i in range(len(ordered) - 1):
                lines.append(f"  \"{ordered[i].id}\" -> \"{ordered[i + 1].id}\";")
            lines.append("}")
            return "\n".join(lines)
        except Exception as e:
            print(f'Failed to generate diagram: {e}')
            raise Exception('Failed to generate workflow diagram. Please try again.')

    async def generate_workflow_diagrams(self, workflow_text: str, files: Optional[List[FileData]] = None) -> WorkflowDiagrams:
        """Generate SEPARATE system and user workflow diagrams from AI-extracted steps."""
        try:
            all_steps = await self._extract_workflow_steps_with_ai(workflow_text, files)
            if not all_steps:
                raise Exception('Could not extract workflow steps from the analysis text')
            system_steps = [s for s in all_steps if s.is_system]
            user_steps = [s for s in all_steps if not s.is_system]
            system_diagram = self._generate_diagram(system_steps)
            user_diagram = self._generate_diagram(user_steps)
            return WorkflowDiagrams(system=system_diagram, user=user_diagram)
        except Exception as e:
            print(f'Error in generateWorkflowDiagrams: {e}')
            raise e

# Chat Service
class ChatService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.config = Config()
    
    async def chat_about_project(self, question: str, project: Dict[str, Any]) -> str:
        """Chat about project using AI."""
        context_files = (project.get('files', []))[:6]
        
        files_block = '\n\n'.join([
            f"### {f['name']}\n\n```\n{f['content'][:1000]}\n```"
            for f in context_files
        ])
        
        system_prompt = f"""You are an expert repository assistant for the project {project.get('repoName', '')}.
You answer developer questions with precise, actionable, technically accurate explanations grounded strictly in the provided repository context.
If information is missing, say what is unknown and suggest where to look.
Prefer concrete code-level references (files, functions, data flow) and short examples."""
        
        user_prompt = f"""CONTEXT FILES:\n{files_block}\n\nPROJECT SUMMARY (if any):\n{project.get('summary', 'N/A')}\n\nQUESTION:\n{question}\n\nRESPONSE REQUIREMENTS:\n- Answer directly and concisely first.\n- Cite specific files/paths when referring to code.\n- If code snippets are needed, keep them short.\n- If uncertain, call out the uncertainty explicitly."""
        
        response = requests.post(
            self.config.MODEL_URL,
            json={
                "model": self.config.MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 800,
                "temperature": 0.2,
                "top_p": 0.9
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=45
        )
        
        if response.status_code != 200:
            raise Exception(f'Chat request failed: {response.text}')
        
        content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        if not content:
            raise Exception('No response from the chat model')
        
        rewritten_content = await rewrite_tone(content, self.api_key, self.config.REWRITER_MODEL)
        return rewritten_content

async def rewrite_tone(response_text: str, api_key: str, model: str) -> str:
    try:
        sys_prompt = (
            "You are a friendly and professional AI assistant. \n"
            "Rewrite the given text to sound natural, conversational, and human-like, \n"
            "while preserving all the technical details and meaning."
        )
        resp = requests.post(
            Config.MODEL_URL,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": response_text},
                ],
                "max_tokens": 800,
                "temperature": 0.3,
                "top_p": 0.9,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=45,
        )
        if resp.status_code == 200:
            rewritten = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if rewritten:
                return rewritten
        return response_text
    except Exception:
        return response_text

# Initialize services
def get_services():
    """Initialize and return all services."""
    if not Config.TOGETHER_API_KEY:
        raise Exception("TOGETHER_API_KEY environment variable is required")
    if not Config.GITHUB_TOKEN:
        raise Exception("GITHUB_TOKEN environment variable is required")
    
    github_service = GitHubService(Config.GITHUB_TOKEN)
    analysis_service = AnalysisService(Config.TOGETHER_API_KEY)
    workflow_service = WorkflowDiagramService(Config.TOGETHER_API_KEY)
    chat_service = ChatService(Config.TOGETHER_API_KEY)
    
    return github_service, analysis_service, workflow_service, chat_service

if __name__ == "__main__":
    print("ProAnalyze Python Version")
    print("Services initialized successfully!")
