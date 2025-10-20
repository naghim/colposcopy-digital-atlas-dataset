# IARC Colposcopy Atlas Dataset & Scraper

A Python-based web scraper for downloading colposcopy case data and images from the [IARC Screening Group Atlas of Colposcopy](https://screening.iarc.fr).

## Overview

This tool scrapes colposcopy case information including:

- Patient metadata (age, HPV status)
- Clinical diagnoses (provisional and histopathology)
- Swede scores
- Management information
- High-resolution colposcopy images at different examination stages

## Requirements

```
Python 3.6+
requests
beautifulsoup4
```

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install requests beautifulsoup4
```

## Usage

### Basic Usage

Run the scraper with default settings:

```bash
python scraper.py
```

The script will:

1. Scrape all cases from the configured URL
2. Extract metadata and image information
3. Save data to a CSV file
4. Prompt you whether to download images

### Customizing the Target URL

Edit the `url` variable in the `main()` function to scrape different diagnostic categories:

```python
# Example URLs:
# High-grade lesions (CIN 2/3):
url = "https://screening.iarc.fr/atlascolpodiag_list.php?FinalDiag=31&e=..."

# Low-grade lesions (CIN 1):
url = "https://screening.iarc.fr/atlascolpodiag_list.php?FinalDiag=06&e=..."
```

## Output Structure

### CSV File Format

The generated CSV file contains the following columns:

| Column                     | Description                                      |
| -------------------------- | ------------------------------------------------ |
| `case_number`              | Sequential case number from the atlas            |
| `case_id`                  | Unique alphanumeric case identifier (e.g., AABB) |
| `age`                      | Patient age                                      |
| `hpv_status`               | HPV test result                                  |
| `provisional_diagnosis`    | Initial clinical diagnosis                       |
| `histopathology_diagnosis` | Final histopathology diagnosis                   |
| `management`               | Clinical management decision                     |
| `swede_score`              | Swede colposcopy scoring                         |
| `num_images`               | Number of images for this case                   |
| `detail_link`              | URL to the case detail page                      |

### Image Directory Structure

```
images_<grade>/
├── case_AABB/
│   ├── metadata.txt
│   ├── 1_After_normal_saline.jpg
│   ├── 2_After_acetic_acid.jpg
│   ├── 3_After_Lugols_iodine.jpg
│   └── ...
├── case_AACC/
│   ├── metadata.txt
│   └── ...
└── ...
```

Each case folder contains:

- **metadata.txt**: Complete case information and image URLs
- **Images**: Numbered by examination stage with descriptive filenames

## Rate Limiting

The scraper implements polite crawling practices:

- 1-second delay between case detail page requests
- 0.5-second delay between image downloads
- Timeout of 30 seconds for all requests
