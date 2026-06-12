from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import os
import asyncio
import re
from app import get_services

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

github_service, analysis_service, workflow_service, chat_service = get_services()

# In-memory session replacement (simple)
session_state = {
	"repo_data": None,
	"analysis": None,
	"workflow": None,
	"chat": []
}

# Jinja filters
@app.template_filter('regex_extract')
def regex_extract(value, pattern):
	try:
		m = re.search(pattern, value or '', flags=re.S)
		return (m.group(1).strip() if m else '')
	except Exception:
		return ''

@app.route("/")
def home():
	return render_template("home.html")

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
	if request.method == "POST":
		repo_url = request.form.get("repo_url", "").strip()
		if not repo_url:
			flash("Please enter a GitHub repository URL.", "warning")
			return redirect(url_for("analyze"))
		try:
			owner, repo = github_service.parse_repo_url(repo_url)
			repo_data = asyncio.run(github_service.fetch_repository_data(owner, repo))
			analysis = asyncio.run(analysis_service.analyze_code(repo_data.files))
			session_state["repo_data"] = repo_data
			session_state["analysis"] = analysis
			session_state["workflow"] = None
			flash("Analysis completed successfully.", "success")
		except Exception as e:
			flash(f"Analysis failed: {str(e)}", "danger")
		return redirect(url_for("analyze"))
	
	repo_data = session_state.get("repo_data")
	analysis = session_state.get("analysis")
	workflow = session_state.get("workflow")
	return render_template("analyze.html", repo_data=repo_data, analysis=analysis, workflow=workflow)

@app.route("/generate-workflows", methods=["POST"]) 
def generate_workflows():
	analysis = session_state.get("analysis")
	if not analysis:
		flash("Please analyze a repository first.", "warning")
		return redirect(url_for("analyze"))
	match = re.search(r"## Project Workflow\n([\s\S]*?)(?=\n## |$)", analysis)
	if not match:
		flash("No workflow information found in the analysis.", "warning")
		return redirect(url_for("analyze"))
	workflow_section = match.group(1)
	try:
		repo = session_state.get("repo_data")
		files = repo.files if repo else None
		diagrams = asyncio.run(workflow_service.generate_workflow_diagrams(workflow_section, files))
		session_state["workflow"] = diagrams
		flash("Workflow diagrams generated.", "success")
	except Exception as e:
		flash(f"Failed to generate workflows: {str(e)}", "danger")
	return redirect(url_for("analyze"))

@app.route("/chat", methods=["GET", "POST"]) 
def chat():
	if request.method == "POST":
		if "load_repo" in request.form:
			repo_url = request.form.get("repo_url", "").strip()
			try:
				owner, repo = github_service.parse_repo_url(repo_url)
				repo_data = asyncio.run(github_service.fetch_repository_data(owner, repo))
				project_ctx = {
					"repoName": repo_data.name,
					"summary": f"{repo_data.description or ''}\nLanguage: {repo_data.language}\nStars: {repo_data.stars} Forks: {repo_data.forks}",
					"files": [{"name": f.path, "content": f.content} for f in repo_data.files]
				}
				session_state["chat_repo"] = project_ctx
				session_state["chat"] = [{"role": "system", "content": "Ask anything about your repository."}]
				flash("Repository loaded for chat.", "success")
			except Exception as e:
				flash(f"Failed to load repository: {str(e)}", "danger")
		elif "send" in request.form:
			message = request.form.get("message", "").strip()
			if message:
				session_state["chat"].append({"role": "user", "content": message})
				try:
					answer = asyncio.run(chat_service.chat_about_project(message, session_state.get("chat_repo", {})))
					session_state["chat"].append({"role": "assistant", "content": answer})
				except Exception as e:
					session_state["chat"].append({"role": "assistant", "content": f"Chat failed: {str(e)}"})
	return render_template("chat.html", messages=session_state.get("chat", []), chat_repo=session_state.get("chat_repo"))

if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True)
