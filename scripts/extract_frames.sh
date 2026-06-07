#!/usr/bin/env bash
#
# extract_frames.sh
#
# Extract frames from 360° MP4 videos using ffmpeg.
#
# Structure expected:
#   data/raw/<FOLDER>/
#     ├── <subfolder_1>/
#     │     ├── video1.mp4
#     │     └── video2.mp4
#     └── <subfolder_2>/
#           └── video3.mp4
#
# For each subfolder, a "frames/" directory is created and frames are
# extracted as JPG files with 5-digit zero-padded numbering:
#   <subfolder>/frames/<video_basename>_%05d.JPG
#
# Usage:
#   ./scripts/extract_frames.sh <folder1> [folder2] ...
#
# Examples:
#   # Process a single folder
#   ./scripts/extract_frames.sh 500_UC_Davic_AIC
#
#   # Process multiple folders
#   ./scripts/extract_frames.sh 500_UC_Davic_AIC 200_NIH_SRLM Deschutes_County_Courthouse
#
#   # Process all folders in data/raw/
#   ./scripts/extract_frames.sh --all

set -euo pipefail

# ── Resolve paths ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RAW_DATA_DIR="${PROJECT_ROOT}/data/raw"

# ── Colors for terminal output ─────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Helper functions ───────────────────────────────────────────────────────
log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    echo -e "${BOLD}Usage:${NC} $0 [--all] [--fps N] [--dry-run] <folder1> [folder2] ..."
    echo ""
    echo "  Extracts frames from MP4 videos inside data/raw/<folder>/<subfolder>/"
    echo ""
    echo "  Options:"
    echo "    --all       Process all folders in data/raw/"
    echo "    --fps N     Extract at N frames per second (default: extract every frame)"
    echo "    --dry-run   Show what would be done without actually running ffmpeg"
    echo "    -h, --help  Show this help message"
    echo ""
    echo "  Examples:"
    echo "    $0 500_UC_Davic_AIC"
    echo "    $0 --fps 1 500_UC_Davic_AIC 200_NIH_SRLM"
    echo "    $0 --all --fps 2"
    exit 0
}

# ── Check dependencies ────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    log_error "ffmpeg is not installed or not in PATH."
    exit 1
fi

# ── Parse arguments ───────────────────────────────────────────────────────
PROCESS_ALL=false
DRY_RUN=false
FPS_FILTER=""
FOLDERS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            PROCESS_ALL=true
            shift
            ;;
        --fps)
            if [[ -z "${2:-}" ]]; then
                log_error "--fps requires a numeric argument"
                exit 1
            fi
            FPS_FILTER="-vf fps=$2"
            log_info "Frame rate set to ${BOLD}$2 fps${NC}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            ;;
        *)
            FOLDERS+=("$1")
            shift
            ;;
    esac
done

# ── Resolve target folders ────────────────────────────────────────────────
if $PROCESS_ALL; then
    if [[ ${#FOLDERS[@]} -gt 0 ]]; then
        log_warn "--all flag ignores explicitly listed folders"
    fi
    FOLDERS=()
    for dir in "${RAW_DATA_DIR}"/*/; do
        dirname="$(basename "$dir")"
        # Skip hidden dirs and checkpoint dirs
        [[ "$dirname" == .* ]] && continue
        FOLDERS+=("$dirname")
    done
fi

if [[ ${#FOLDERS[@]} -eq 0 ]]; then
    log_error "No folders specified. Use --all or provide folder names."
    echo ""
    usage
fi

# ── Validate that data/raw exists ─────────────────────────────────────────
if [[ ! -d "$RAW_DATA_DIR" ]]; then
    log_error "Raw data directory not found: ${RAW_DATA_DIR}"
    exit 1
fi

# ── Process each folder ──────────────────────────────────────────────────
TOTAL_VIDEOS=0
TOTAL_SKIPPED=0
TOTAL_ERRORS=0

for folder in "${FOLDERS[@]}"; do
    FOLDER_PATH="${RAW_DATA_DIR}/${folder}"

    if [[ ! -d "$FOLDER_PATH" ]]; then
        log_warn "Folder not found, skipping: ${FOLDER_PATH}"
        continue
    fi

    echo ""
    echo -e "${BOLD}━━━ Processing: ${CYAN}${folder}${NC} ${BOLD}━━━${NC}"

    # Iterate over subfolders (date-based folders like Nov_6_2025, Feb_9_2026)
    for subfolder in "${FOLDER_PATH}"/*/; do
        [[ ! -d "$subfolder" ]] && continue

        subfolder_name="$(basename "$subfolder")"
        # Skip hidden dirs and checkpoint dirs
        [[ "$subfolder_name" == .* ]] && continue

        FRAMES_DIR="${subfolder}frames"

        # Find all MP4 files in this subfolder
        mp4_files=()
        while IFS= read -r -d '' f; do
            mp4_files+=("$f")
        done < <(find "$subfolder" -maxdepth 1 -iname '*.mp4' -print0 | sort -z)

        if [[ ${#mp4_files[@]} -eq 0 ]]; then
            log_warn "  No MP4 files in ${folder}/${subfolder_name}, skipping"
            continue
        fi

        log_info "  Subfolder: ${BOLD}${subfolder_name}${NC} (${#mp4_files[@]} video(s))"

        # Create frames directory
        if ! $DRY_RUN; then
            mkdir -p "$FRAMES_DIR"
        fi

        for mp4_file in "${mp4_files[@]}"; do
            video_basename="$(basename "$mp4_file" .mp4)"
            # Also handle .MP4 extension
            video_basename="$(basename "$video_basename" .MP4)"
            output_pattern="${FRAMES_DIR}/${video_basename}_IMG_%05d.JPG"

            # Check if frames already exist for this video
            existing_frames=0
            if [[ -d "$FRAMES_DIR" ]]; then
                existing_frames=$(find "$FRAMES_DIR" -maxdepth 1 -name "${video_basename}_IMG_*.JPG" 2>/dev/null | wc -l)
            fi
            if [[ $existing_frames -gt 0 ]]; then
                log_warn "    Skipping ${video_basename} — ${existing_frames} frames already exist"
                ((TOTAL_SKIPPED+=1)) || true
                continue
            fi

            if $DRY_RUN; then
                echo -e "    ${YELLOW}[DRY-RUN]${NC} ffmpeg -i ${mp4_file} ${FPS_FILTER} ${output_pattern}"
                ((TOTAL_VIDEOS+=1)) || true
                continue
            fi

            log_info "    Extracting: ${video_basename}"
            log_info "    Output:     ${FRAMES_DIR}/"

            # Run ffmpeg
            # shellcheck disable=SC2086
            if ffmpeg -i "$mp4_file" $FPS_FILTER "$output_pattern" \
                -hide_banner -loglevel warning -y; then

                frame_count=$(find "$FRAMES_DIR" -maxdepth 1 -name "${video_basename}_IMG_*.JPG" | wc -l)
                log_success "    Extracted ${BOLD}${frame_count}${NC} frames from ${video_basename}"
                ((TOTAL_VIDEOS+=1)) || true
            else
                log_error "    Failed to extract frames from ${video_basename}"
                ((TOTAL_ERRORS+=1)) || true
            fi
        done
    done
done

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━ Summary ━━━${NC}"
echo -e "  Videos processed: ${GREEN}${TOTAL_VIDEOS}${NC}"
echo -e "  Videos skipped:   ${YELLOW}${TOTAL_SKIPPED}${NC}"
echo -e "  Errors:           ${RED}${TOTAL_ERRORS}${NC}"

if [[ $TOTAL_ERRORS -gt 0 ]]; then
    exit 1
fi
