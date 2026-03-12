FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec streamlit run ai_analysis_interface_v4.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
