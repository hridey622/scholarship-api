"""Form filling service using Selenium with headless Chrome"""
import time
import asyncio
import threading
import os
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from ..config import get_settings


class FormFillerService:
    """Service for filling scholarship forms using Selenium"""
    
    def __init__(self):
        self._settings = get_settings()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "..", "screenshots")
        os.makedirs(self._screenshots_dir, exist_ok=True)
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create a headless Chrome driver"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def _js_click(self, driver, wait, xpath: str) -> bool:
        """Click element using JavaScript"""
        try:
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", element)
            time.sleep(0.8)
            return True
        except Exception as e:
            print(f"Click failed for {xpath}: {e}")
            return False
    
    def _fill_dob_with_datepicker(self, driver, wait, dob_str: str) -> bool:
        """Fill DOB using Angular Material datepicker"""
        try:
            # Parse DOB
            if "/" in dob_str:
                day, month, year = dob_str.split("/")
            elif "-" in dob_str:
                parts = dob_str.split("-")
                if len(parts[0]) == 4:  # YYYY-MM-DD
                    year, month, day = parts
                else:  # DD-MM-YYYY
                    day, month, year = parts
            else:
                return False
            
            day = str(int(day))  # Remove leading zero
            month_map = {
                "01": "JAN", "02": "FEB", "03": "MAR", "04": "APR",
                "05": "MAY", "06": "JUN", "07": "JUL", "08": "AUG",
                "09": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"
            }
            month_abbr = month_map[month.zfill(2)]
            
            # Open datepicker
            self._js_click(driver, wait, '//*[@id="mat-input-1"]')
            
            # Switch to multi-year view
            self._js_click(
                driver, wait,
                "//mat-calendar[@id='mat-datepicker-0']//button[contains(@class, 'mat-calendar-period-button')]"
            )
            
            wait.until(EC.presence_of_element_located((By.XPATH, "//mat-multi-year-view")))
            
            # Select year
            self._js_click(
                driver, wait,
                f"//mat-multi-year-view//button[@aria-label='{year}' or .//span[contains(text(),'{year}') or normalize-space(.)='{year}']]"
            )
            
            # Select month
            self._js_click(
                driver, wait,
                f"//mat-year-view//button[.//span[contains(text(),'{month_abbr}')]]"
            )
            
            # Select day
            self._js_click(
                driver, wait,
                f"//mat-month-view//button[.//span[contains(@class, 'mat-calendar-body-cell-content') and normalize-space(text())='{day}']]"
            )
            
            return True
        except Exception as e:
            print(f"DOB fill failed: {e}")
            return False
    
    def _fill_form_sync(
        self, 
        user_data: Dict[str, str], 
        session_id: str
    ) -> Tuple[bool, str, List[str], Optional[str]]:
        """
        Synchronously fill the form (runs in thread pool).
        
        Returns:
            Tuple of (success, message, errors, screenshot_path)
        """
        driver = None
        errors: List[str] = []
        screenshot_path = None
        
        try:
            driver = self._create_driver()
            wait = WebDriverWait(driver, 20)
            
            # Navigate to form
            driver.get(self._settings.form_url)
            
            # Wait for form to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "mat-select"))
            )
            time.sleep(2)  # Extra wait for Angular to fully load
            
            # Text input fields mapping
            text_fields = {
                "name": "mat-input-0",
                "annual_family_income": "mat-input-2",
                "xii_roll_no": "mat-input-5",
                "twelfthPercentage": "mat-input-6",
                "x_roll_no": "mat-input-8",
                "tenthPercentage": "mat-input-9",
                "competitiveRollno": "mat-input-10",
            }
            
            # Fill text inputs
            for field_key, element_id in text_fields.items():
                if user_data.get(field_key):
                    try:
                        field = driver.find_element(By.ID, element_id)
                        field.clear()
                        field.send_keys(str(user_data[field_key]))
                    except Exception as e:
                        errors.append(f"Could not fill {field_key}: {str(e)}")
            
            # Fill DOB
            if user_data.get("dob"):
                try:
                    self._fill_dob_with_datepicker(driver, wait, user_data["dob"])
                except Exception as e:
                    errors.append(f"DOB selection failed: {str(e)}")
            
            # Select dropdown fields mapping
            select_fields = {
                "d_state_id": "mat-select-0",
                "gender": "mat-select-2",
                "religion": "mat-select-8",
                "community": "mat-select-10",
                "maritalStatus": "mat-select-4",
                "c_course_id": "mat-select-22",
                "parent_profession": "mat-select-6",
                "hosteler": "mat-select-14",
                "competitiveExam": "mat-select-28",
            }
            
            # Fill select dropdowns
            for user_field, form_field in select_fields.items():
                if user_data.get(user_field):
                    try:
                        combo = wait.until(EC.presence_of_element_located((By.ID, form_field)))
                        driver.execute_script("arguments[0].click();", combo)
                        time.sleep(0.5)
                        
                        option = wait.until(
                            EC.element_to_be_clickable((
                                By.XPATH, 
                                f"//mat-option//span[text()='{user_data[user_field]}']"
                            ))
                        )
                        option.click()
                        time.sleep(0.3)
                    except Exception as e:
                        errors.append(f"Could not select {user_field}: {str(e)}")
            
            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(
                self._screenshots_dir, 
                f"form_{session_id}_{timestamp}.png"
            )
            driver.save_screenshot(screenshot_path)
            
            if errors:
                return (
                    True, 
                    f"Form partially filled with {len(errors)} errors. CAPTCHA required.", 
                    errors, 
                    screenshot_path
                )
            else:
                return (
                    True, 
                    "Form filled successfully. CAPTCHA required for submission.", 
                    [], 
                    screenshot_path
                )
                
        except Exception as e:
            return (False, f"Form filling failed: {str(e)}", [str(e)], screenshot_path)
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    async def fill_form(
        self, 
        user_data: Dict[str, str], 
        session_id: str
    ) -> Tuple[bool, str, List[str], Optional[str]]:
        """
        Fill the scholarship form with provided data.
        
        Args:
            user_data: Dictionary of form field values
            session_id: Session ID for screenshot naming
            
        Returns:
            Tuple of (success, message, errors, screenshot_path)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._fill_form_sync,
            user_data,
            session_id
        )
    
    def get_screenshot_path(self, session_id: str) -> Optional[str]:
        """Get the latest screenshot for a session"""
        try:
            screenshots = [
                f for f in os.listdir(self._screenshots_dir)
                if f.startswith(f"form_{session_id}_") and f.endswith(".png")
            ]
            if screenshots:
                screenshots.sort(reverse=True)
                return os.path.join(self._screenshots_dir, screenshots[0])
            return None
        except:
            return None
