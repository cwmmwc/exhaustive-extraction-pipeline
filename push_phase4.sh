#!/bin/bash
# Push Phase 4 validation files to HPC
set -e
CTL=/tmp/cwm6w-hpc-p4-$$
HOST=cwm6w@login.hpc.virginia.edu
REPO=$HOME/projects/exhaustive-extraction-pipeline
ssh -M -S "$CTL" -o ControlPersist=10m -fN "$HOST"
trap 'ssh -S "$CTL" -O exit "$HOST" 2>/dev/null || true' EXIT
SCP="scp -o ControlPath=$CTL"
SSH="ssh -S $CTL $HOST"
REMOTE="$HOST:/project/LawData/kimi-extraction"

echo "Creating remote directories..."
$SSH "mkdir -p /project/LawData/kimi-extraction/code/prompts /project/LawData/kimi-extraction/code/circular_2464_extractions/validation_samples /project/LawData/kimi-extraction/code/circular_2464_extractions/split_documents/affidavits /project/LawData/kimi-extraction/code/circular_2464_extractions/split_documents/questionnaires /project/LawData/kimi-extraction/code/circular_2464_extractions/split_documents/agency_narratives /project/LawData/kimi-extraction/code/circular_2464_extractions/split_documents/ledgers /project/LawData/kimi-extraction/code/circular_2464_extractions/standalone"

echo "Pushing code..."
$SCP "$REPO/run_phase4_validation.py" "$REMOTE/code/"

echo "Pushing prompts..."
$SCP "$REPO/prompts/extraction_single_document.md" "$REPO/prompts/extraction_ledger.md" "$REMOTE/code/prompts/"

echo "Pushing sample IDs..."
$SCP "$REPO/circular_2464_extractions/validation_samples/phase4_sample_ids.csv" "$REMOTE/code/circular_2464_extractions/validation_samples/"

echo "Pushing manifest..."
$SCP "$REPO/circular_2464_extractions/split_documents/manifest.csv" "$REMOTE/code/circular_2464_extractions/split_documents/"

echo "Pushing split documents (affidavits)..."
rsync -avh --progress -e "ssh -o ControlPath=$CTL" "$REPO/circular_2464_extractions/split_documents/affidavits/" "$REMOTE/code/circular_2464_extractions/split_documents/affidavits/"

echo "Pushing split documents (questionnaires)..."
rsync -avh --progress -e "ssh -o ControlPath=$CTL" "$REPO/circular_2464_extractions/split_documents/questionnaires/" "$REMOTE/code/circular_2464_extractions/split_documents/questionnaires/"

echo "Pushing split documents (agency_narratives)..."
rsync -avh --progress -e "ssh -o ControlPath=$CTL" "$REPO/circular_2464_extractions/split_documents/agency_narratives/" "$REMOTE/code/circular_2464_extractions/split_documents/agency_narratives/"

echo "Pushing split documents (ledgers)..."
rsync -avh --progress -e "ssh -o ControlPath=$CTL" "$REPO/circular_2464_extractions/split_documents/ledgers/" "$REMOTE/code/circular_2464_extractions/split_documents/ledgers/"

echo "Pushing standalone ledger..."
$SCP "$REPO/circular_2464_extractions/standalone/fee_patent_ledger_part11.pdf" "$REMOTE/code/circular_2464_extractions/standalone/"

echo "Pushing SLURM script..."
$SCP "$REPO/hpc/run_phase4_kimi.slurm" "$REMOTE/hpc/"

echo ""
echo "Done. SSH to HPC and run:"
echo "  cd /project/LawData/kimi-extraction/code && sbatch /project/LawData/kimi-extraction/hpc/run_phase4_kimi.slurm"
