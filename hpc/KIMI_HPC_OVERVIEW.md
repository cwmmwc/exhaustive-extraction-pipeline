# Running Kimi K2.5 Extraction on UVA HPC

**Author:** Christian McMillen, Department of History, UVA
**Date:** 2026-03-26
**Allocation:** LawData

---

## What This Project Does

I have a corpus of ~5,000 historical PDF documents (139 million words) from federal agencies documenting Native American land dispossession, 1880-1990. The documents are OCR-digitized BIA administrative records, congressional hearings, fee patent files, correspondence, and litigation records.

I use AI models to perform **structured extraction** from these documents: reading the full text and returning structured JSON containing every person, organization, event, financial transaction, legal relationship, and fee patent record mentioned. Fee patents are the atomic unit of land dispossession in this research -- they link an individual allottee to a specific parcel of land, a date, a legal mechanism, a buyer, and a price. Building a comprehensive roster of every individual affected is the core research goal.

The extracted data goes into a PostgreSQL database that powers a Streamlit analysis interface for historical research.

## Why Kimi K2.5

I've been benchmarking open-source models against Claude (Anthropic's commercial model) for this extraction task. Most open-source models perform poorly on the hardest category -- fee patents -- because extracting them requires comprehending that a sequence of narrative sentences about an individual constitutes a structured case history. Llama 3.3 70B, for example, finds only 10% of the fee patents that Claude finds.

**Kimi K2.5** (by Moonshot AI) broke that pattern. On a 221-page test document, Kimi found 268 unique fee patent allottees versus Claude's 169 -- 59% more named individuals whose dispossession is documented in the historical record. No hallucinated names. It also correctly distinguishes between different legal mechanisms of dispossession (application vs. certificate of competency), which Claude labels generically. At 73% of Claude's overall extraction volume, it's the best open-source model I've tested.

The goal on the HPC is to run Kimi K2.5 on the full corpus to build the most complete roster of individuals possible, then use Claude (via API) for targeted deep extraction on narrative-heavy documents where it has an advantage.

## The Model

- **Model:** Kimi K2.5 (`moonshotai/Kimi-K2.5` on HuggingFace)
- **Architecture:** Mixture-of-Experts (MoE), 1 trillion total parameters, 32B active per token, 384 experts
- **Weight size:** ~549GB (mixed BF16 attention layers + INT4 quantized expert weights)
- **GPU requirement:** 8x A100 80GB (549GB of weights + KV cache overhead)
- **Context window:** 256K tokens (we use ~40K-character chunks, well within this)
- **vLLM support:** Official -- vLLM has a published recipe for this model

## Architecture on the HPC

Following the server/worker pattern from the getting-started guide:

### GPU Server Job (`start_kimi_server.slurm`)

A long-running vLLM server on a GPU node:

- **Partition:** gpu
- **Resources:** 8x A100 80GB, 32 CPUs, 500GB RAM
- **Runtime:** Up to 3 days
- **What it does:** Loads Kimi K2.5 into GPU memory using tensor parallelism across all 8 GPUs, then exposes an OpenAI-compatible REST API on port 8000
- **Server address:** Written to `/project/LawData/kimi-extraction/logs/server_address.txt` at startup so worker jobs can find it

### CPU Worker Job (`run_kimi_extraction.slurm`)

One or more extraction workers on the standard partition:

- **Partition:** standard (no GPU needed)
- **Resources:** 8 CPUs, 32GB RAM
- **Runtime:** Up to 2 days
- **What it does:** Reads PDFs from a staging directory, extracts text with PyMuPDF, splits into 40,000-character chunks with 5,000-character overlap, sends each chunk to the vLLM server via HTTP, parses the JSON response, and saves results
- **Skip-on-exists:** If a document has already been extracted (output JSON exists), it skips it. Safe to resubmit if the job dies mid-run.
- **Can process one PDF or all PDFs** in the staging directory, controlled by the `PDF` environment variable at submission time

## Directory Layout

```
/project/LawData/
├── models/
│   ├── Kimi-K2.5/                  # Model weights (~549GB)
│   └── container/
│       └── vllm_0.14.1-cu130.sif   # Shared vLLM container
├── kimi-extraction/
│   ├── code/
│   │   └── extract_single_pdf.py   # Extraction script
│   ├── pdfs/                       # Stage input PDFs here
│   ├── outputs/                    # Extraction results (JSON per document)
│   └── logs/
│       ├── server_address.txt      # Written by server at startup
│       ├── server_<jobid>.out      # Server stdout
│       └── extract_<jobid>.out     # Worker stdout
└── exhaustive-extraction-pipeline/ # Git repo (SLURM scripts, comparison tools)

/scratch/cwm6w/
├── containers/
│   └── vllm_kimi.sif              # Fresh vLLM container with Kimi support
└── fakehome/.cache/
    ├── huggingface/                # HF cache
    ├── vllm/                       # vLLM cache
    ├── flashinfer/                 # FlashInfer cache
    └── triton/                     # Triton cache
```

## How to Run It

```bash
# One-time setup (already done)
bash hpc/setup_kimi.sh

# Stage PDFs
cp /path/to/pdfs/*.pdf /project/LawData/kimi-extraction/pdfs/

# Start the server
sbatch hpc/start_kimi_server.slurm

# Submit the extraction worker
sbatch --export=PDF=ALL hpc/run_kimi_extraction.slurm

# Or test with a single document first
sbatch --export=PDF="1921 CCF 56074-21-312 GS.pdf" hpc/run_kimi_extraction.slurm

# Monitor
squeue -u $USER
tail -f /project/LawData/kimi-extraction/logs/server_*.out
```

## Resource Usage Notes

The 8x A100 80GB request is the largest single-node GPU allocation possible. A few things to be aware of:

- **Queue wait times** may be significant. 8-GPU jobs depend on a full node being available. Submitting during off-peak hours (evenings, weekends) helps.
- **The server job runs for up to 3 days.** Once the model is loaded (~5-10 minutes), it sits idle between requests and doesn't consume compute beyond holding the GPUs. The actual work is driven by the worker jobs.
- **Worker jobs are cheap.** They run on the standard partition with no GPU, just sending HTTP requests to the server. Multiple workers could run in parallel against the same server if needed.
- **Extraction speed per document** depends on document length. A 221-page document (15 chunks) took about 20 minutes via Together AI's hosted Kimi; on-HPC performance will depend on the vLLM serving throughput with 8-way tensor parallelism.
- **Total corpus estimate:** 5,000 documents at an average of ~5 chunks each = ~25,000 inference calls. At the speeds observed on Together AI, this would take roughly 3-5 days of continuous server time, though HPC throughput may differ.

## Questions I Have

1. Is 8x A100 80GB reasonable for a multi-day job on this allocation, or should I expect the scheduler to deprioritize me quickly?
2. Is there a preferred way to handle the 549GB model download? I ran it on the login node and it took several hours. Should I have submitted it as a SLURM job instead?
3. The existing shared container (`vllm_0.14.1-cu130.sif`) may not have the `transformers >= 4.57.1` that Kimi requires. I'm building a fresh container at `/scratch/cwm6w/containers/vllm_kimi.sif`. Should I put this somewhere shared if others want to use Kimi?

## Background

The full pipeline, model comparison results, and extraction schema are documented in the project repository:
https://github.com/cwmmwc/exhaustive-extraction-pipeline

The key benchmark document is `comparisons/MODEL_COMPARISON_SUMMARY.md`, which includes detailed side-by-side comparisons of Claude, Kimi K2.5, Llama 3.3 70B, Llama 4 Maverick, and Llama 4 Scout across extraction and synthesis tasks.
