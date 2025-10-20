#!/usr/bin/env python3
"""
Basic HTML scraper for IARC Atlas of Colposcopy
Scrapes case data including images and diagnostic information
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urljoin
import time
import re


class ColposcopyScraper:
    def __init__(self, base_url="https://screening.iarc.fr"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_case_id_from_image(self, img_src):
        """Extract case ID from image filename (e.g., AABB0.jpg -> AABB)"""
        if img_src:
            filename = os.path.basename(img_src)
            # Remove extension and trailing number
            match = re.match(r'([A-Z]+)\d+\.', filename)
            if match:
                return match.group(1)
        return None
    
    def scrape_list_page(self, url):
        """
        Scrape the colposcopy atlas list page to get case IDs and basic info
        
        Args:
            url: Full URL to scrape
            
        Returns:
            List of dictionaries containing case data with detail links
        """
        print(f"Fetching list page: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all table rows
            cases = []
            
            table = soup.find('div', class_='col-sm-11')
            if table:
                table = table.find('table', class_='table table-striped table-hover')
            
            if not table:
                print("No table found on page")
                return cases
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cols = row.find_all('td')
                
                if len(cols) >= 5:
                    # Extract case number from table
                    case_number = cols[0].get_text(strip=True)
                    
                    # Extract diagnosis from last column
                    diagnosis_col = cols[4]
                    diagnosis_font = diagnosis_col.find('font')
                    histopathology_diagnosis = diagnosis_font.get_text(strip=True) if diagnosis_font else cols[4].get_text(strip=True)
                    
                    # Extract thumbnail image to get case ID
                    img_tag = cols[1].find('img')
                    case_id = None
                    if img_tag and img_tag.get('src'):
                        case_id = self.extract_case_id_from_image(img_tag.get('src'))
                    
                    # Extract detail link - clicking on image leads to detail page
                    detail_link = None
                    link_tag = cols[1].find('a')
                    if link_tag and link_tag.get('href'):
                        detail_link = urljoin(self.base_url, link_tag.get('href'))
                    
                    case_data = {
                        'case_number': case_number,
                        'case_id': case_id,
                        'histopathology_diagnosis': histopathology_diagnosis,
                        'detail_link': detail_link
                    }
                    
                    cases.append(case_data)
                    print(f"Found Case {case_number} (ID: {case_id})")
            
            print(f"Total cases found on list page: {len(cases)}")
            return cases
            
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return []
    
    def scrape_detail_page(self, detail_url, case_data):
        """
        Scrape the detail page for a specific case to get all images and metadata
        
        Args:
            detail_url: URL to the case detail page
            case_data: Dictionary with basic case info from list page
            
        Returns:
            Updated case_data dictionary with complete information
        """
        print(f"  Fetching detail page: {detail_url}")
        
        try:
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main content div
            content_div = soup.find('div', class_='col-sm-11')
            
            if not content_div:
                print(f"  Warning: Could not find content div for case {case_data['case_number']}")
                return case_data
            
            # Extract age and HPV status
            age_and_hpv = content_div.find_all('font')
            age_li = age_and_hpv[1]
            if age_li:
                age_b = age_li.find_next('b')
                case_data['age'] = age_b.get_text(strip=True) if age_b else 'Unknown'

            hpv_li = age_and_hpv[2]
            if hpv_li:
                hpv_b = hpv_li.find_next('b')
                case_data['hpv_status'] = hpv_b.get_text(strip=True) if hpv_b else 'Unknown'
                
            # Extract all images from the detail page
            images = []
            thumbnails = content_div.find_all('div', class_='col-md-13 thumbnail')
            
            for idx, thumbnail in enumerate(thumbnails):
                # Find the fancybox link that contains the full image
                fancybox = thumbnail.find('a', class_='fancybox')
                if fancybox and fancybox.get('href'):
                    img_url = urljoin(self.base_url, fancybox.get('href'))
                    img_title = fancybox.get('title', '')
                    
                    # Find the image stage/description (After normal saline, After acetic acid, etc.)
                    stage_font = thumbnail.find_next('font')
                    stage = 'Unknown'
                    if stage_font:
                        stage_b = stage_font.find('b')
                        if stage_b:
                            stage = stage_b.get_text(strip=True)
                    
                    images.append({
                        'url': img_url,
                        'stage': stage,
                        'description': img_title,
                        'order': idx + 1
                    })
            
            case_data['images'] = images
            print(f"  Found {len(images)} images for case {case_data['case_number']}")
            
            # Extract provisional diagnosis from case summary
            prov_diag = content_div.find('font', string=re.compile(r'Provisional diagnosis:'))
            if prov_diag:
                prov_td = prov_diag.find_next('td')
                if prov_td:
                    prov_b = prov_td.find('b')
                    case_data['provisional_diagnosis'] = prov_b.get_text(strip=True) if prov_b else prov_td.get_text(strip=True)
            
            # Extract management
            management = content_div.find('font', string=re.compile(r'Management:'))
            if management:
                mgmt_td = management.find_next('td')
                if mgmt_td:
                    mgmt_b = mgmt_td.find('b')
                    case_data['management'] = mgmt_b.get_text(strip=True) if mgmt_b else mgmt_td.get_text(strip=True)
            
            # Extract Swede score
            score_tags = content_div.find_all("font")
            for tag in score_tags:
                if "Swede score:" in tag.text:
                    score_tag = [tag]
            if score_tag:
                next_font = score_tag[0].find_next("font", color="#FFAB19")
                score = next_font.text.strip() if next_font else None
            else:
                score = None
            case_data['swede_score'] = score

            return case_data
            
        except requests.RequestException as e:
            print(f"  Error fetching detail page: {e}")
            return case_data
    
    def scrape_all_cases(self, list_url):
        """
        Scrape all cases from list page and their detail pages
        
        Args:
            list_url: URL to the list page
            
        Returns:
            List of complete case data dictionaries
        """
        # First, get all cases from the list page
        cases = self.scrape_list_page(list_url)
        
        # Then, scrape each detail page
        complete_cases = []
        for idx, case in enumerate(cases, 1):
            print(f"\nProcessing case {idx}/{len(cases)}: {case['case_number']}")
            
            if case.get('detail_link'):
                complete_case = self.scrape_detail_page(case['detail_link'], case)
                complete_cases.append(complete_case)
                
                # Be polite - wait between requests
                time.sleep(1)
            else:
                print(f"  Warning: No detail link for case {case['case_number']}")
                complete_cases.append(case)
        
        return complete_cases
    
    def save_to_csv(self, cases, filename='colposcopy_cases.csv'):
        """
        Save scraped data to CSV file
        
        Args:
            cases: List of case dictionaries
            filename: Output CSV filename
        """
        if not cases:
            print("No cases to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['case_number', 'case_id', 'age', 'hpv_status', 
                         'provisional_diagnosis', 'histopathology_diagnosis', 
                         'management', 'swede_score', 'num_images', 
                         'detail_link']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for case in cases:
                # Create a simplified row for CSV
                row = {
                    'case_number': case.get('case_number', ''),
                    'case_id': case.get('case_id', ''),
                    'age': case.get('age', ''),
                    'hpv_status': case.get('hpv_status', ''),
                    'provisional_diagnosis': case.get('provisional_diagnosis', ''),
                    'histopathology_diagnosis': case.get('histopathology_diagnosis', ''),
                    'management': case.get('management', ''),
                    'swede_score': case.get('swede_score', ''),
                    'num_images': len(case.get('images', [])),
                    'detail_link': case.get('detail_link', '')
                }
                writer.writerow(row)
        
        print(f"\nData saved to {filename}")
    
    def download_images(self, cases, output_dir='images'):
        """
        Download images from scraped cases
        
        Args:
            cases: List of case dictionaries
            output_dir: Directory to save images
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        total_images = sum(len(case.get('images', [])) for case in cases)
        downloaded = 0
        
        print(f"\nStarting download of {total_images} images from {len(cases)} cases...")
        
        for case in cases:
            case_num = case.get('case_number', 'unknown')
            case_id = case.get('case_id', case_num)
            case_dir = os.path.join(output_dir, f"case_{case_id}")
            
            if not os.path.exists(case_dir):
                os.makedirs(case_dir)
            
            # Save case metadata
            metadata_file = os.path.join(case_dir, 'metadata.txt')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.write(f"Case Number: {case.get('case_number', '')}\n")
                f.write(f"Case ID: {case.get('case_id', '')}\n")
                f.write(f"Age: {case.get('age', '')}\n")
                f.write(f"HPV Status: {case.get('hpv_status', '')}\n")
                f.write(f"Provisional Diagnosis: {case.get('provisional_diagnosis', '')}\n")
                f.write(f"Histopathology Diagnosis: {case.get('histopathology_diagnosis', '')}\n")
                f.write(f"Management: {case.get('management', '')}\n")
                f.write(f"Swede Score: {case.get('swede_score', '')}\n")
                f.write(f"Detail Link: {case.get('detail_link', '')}\n\n")
                f.write("Images:\n")
                for img in case.get('images', []):
                    f.write(f"  {img['order']}. {img['stage']}: {img['url']}\n")
            
            for img_data in case.get('images', []):
                img_url = img_data['url']
                stage = img_data['stage'].replace(' ', '_').replace('/', '_')
                order = img_data['order']
                
                try:
                    print(f"  [{downloaded+1}/{total_images}] Downloading {case_id} - {stage}...")
                    response = self.session.get(img_url, timeout=30)
                    response.raise_for_status()
                    
                    # Get file extension from URL
                    ext = os.path.splitext(img_url)[1] or '.jpg'
                    filename = os.path.join(case_dir, f"{order}_{stage}{ext}")
                    
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded += 1
                    time.sleep(0.5)  # Be polite, don't hammer the server
                    
                except requests.RequestException as e:
                    print(f"  Error downloading {img_url}: {e}")
        
        print(f"\nDownload complete! {downloaded}/{total_images} images downloaded successfully.")


def main():
    # URL to scrape
    #url = "https://screening.iarc.fr/atlascolpodiag_list.php?FinalDiag=06&e=,0,1,2,3,8,10,15,19,30,31,43,46,47,60,61,68,73,83,88,89,93,96,102,105,111#0"
    url = "https://screening.iarc.fr/atlascolpodiag_list.php?FinalDiag=31&e=,0,1,2,3,8,10,15,19,30,31,43,46,47,60,61,68,73,83,88,89,93,96,102,105,111#0"
    # Create scraper instance
    scraper = ColposcopyScraper()
    
    # Scrape all cases (list page + detail pages)
    print("=" * 70)
    print("IARC Atlas of Colposcopy Scraper")
    print("=" * 70)
    cases = scraper.scrape_all_cases(url)
    
    # Save to CSV
    if cases:
        scraper.save_to_csv(cases)
        
        # Optional: Download images
        print("\n" + "=" * 70)
        download_choice = input("Do you want to download all images? (y/n): ").lower()
        if download_choice == 'y':
            scraper.download_images(cases)
            print("\n" + "=" * 70)
            print("All done!")
            print("=" * 70)
    else:
        print("No cases were scraped.")


if __name__ == "__main__":
    main()
