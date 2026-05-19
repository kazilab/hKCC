FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY db ./db
COPY api ./api
COPY app ./app
COPY streamlit_app.py data.js ./
RUN pip install --no-cache-dir -e .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0"]
