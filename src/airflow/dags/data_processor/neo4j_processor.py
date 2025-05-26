"""
Neo4j Data Processor for laptop data import
Handles comprehensive data extraction and Cypher query generation
"""

import json
import logging
import re
import os
from typing import Dict, List, Any, Tuple


class Neo4jDataProcessor:
    """
    Processes laptop data from JSON files and generates comprehensive Cypher queries
    for Neo4j import with full schema support including all available fields
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the Neo4j Data Processor
        
        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        
    def process_data_file(self, json_file_path: str) -> str:
        """
        Process a JSON data file and generate comprehensive Cypher import queries
        
        Args:
            json_file_path: Path to the JSON file containing laptop data
            
        Returns:
            str: Path to the generated Cypher import file
            
        Raises:
            ValueError: If file path is invalid or data is malformed
            FileNotFoundError: If the JSON file doesn't exist
        """
        if not json_file_path:
            raise ValueError("No JSON file path provided")
            
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")
        
        try:
            # Load and validate JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle data structure - check if it has metadata wrapper or is direct products
            if isinstance(data, dict) and 'products' in data:
                # New format with metadata wrapper
                products_data = data['products']
                self.logger.info(f"Processing data with metadata wrapper. Found {len(products_data)} products")
            elif isinstance(data, dict):
                # Old format - direct dictionary of products
                products_data = data
                self.logger.info(f"Processing data in legacy format. Found {len(products_data)} products")
            else:
                raise ValueError("Invalid JSON structure - expected dictionary")
            
            # Generate comprehensive Cypher queries
            cypher_queries = self._generate_cypher_queries(products_data)
            
            # Save queries to file
            import_file = json_file_path.replace('.json', '_comprehensive_import.cypher')
            self._save_cypher_queries(cypher_queries, import_file)
            
            self.logger.info(f"Generated {len(cypher_queries)} comprehensive Cypher queries for Laptop schema in {import_file}")
            
            return import_file
            
        except Exception as e:
            self.logger.error(f"Failed to process data file {json_file_path}: {str(e)}", exc_info=True)
            raise
    
    def _generate_cypher_queries(self, products_data: Dict[str, Any]) -> List[str]:
        """
        Generate comprehensive Cypher queries from laptop products data
        
        Args:
            products_data: Dictionary containing laptop product data
            
        Returns:
            List[str]: List of Cypher queries for Neo4j import
        """
        cypher_queries = []
        processed_count = 0
        skipped_no_name = 0
        skipped_empty_name = 0
        skipped_insufficient_data = 0
        
        for url, product_data in products_data.items():
            if not isinstance(product_data, dict) or 'Tên máy' not in product_data:
                skipped_no_name += 1
                self.logger.debug(f"Skipping product without 'Tên máy': {url}")
                continue
            
            # Skip products with empty or invalid data
            if not product_data.get('Tên máy') or product_data.get('Tên máy') == '':
                skipped_empty_name += 1
                self.logger.debug(f"Skipping product with empty name: {url}")
                continue
            
            # Extract and process all product information
            laptop_info = self._extract_laptop_info(url, product_data)
            
            if not laptop_info:
                skipped_insufficient_data += 1
                self.logger.debug(f"Skipping laptop with insufficient data: {url}")
                continue
            
            # Generate queries for this laptop
            laptop_queries = self._generate_laptop_queries(url, laptop_info)
            cypher_queries.extend(laptop_queries)
            processed_count += 1
        
        # Log summary
        total_products = len(products_data)
        self.logger.info(f"Processing summary: {total_products} total products")
        self.logger.info(f"  - Processed successfully: {processed_count}")
        self.logger.info(f"  - Skipped (no 'Tên máy' field): {skipped_no_name}")
        self.logger.info(f"  - Skipped (empty name): {skipped_empty_name}")
        self.logger.info(f"  - Skipped (insufficient data): {skipped_insufficient_data}")
        
        return cypher_queries
    
    def _extract_laptop_info(self, url: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and clean all laptop information from product data
        
        Args:
            url: Product URL identifier
            product_data: Raw product data dictionary
            
        Returns:
            Dict[str, Any]: Cleaned and structured laptop information
        """
        # Basic information
        laptop_name = str(product_data.get('Tên máy', '')).replace("'", "\\'").strip()
        description = str(product_data.get('Mô tả chi tiết', '')).replace("'", "\\'")[:2000]
        brand_name = str(product_data.get('Hãng', 'Unknown')).replace("'", "\\'").strip()
        product_url = str(product_data.get('URL', url)).replace("'", "\\'")
        
        # Skip if essential data is missing
        if not laptop_name or not brand_name or brand_name == 'Unknown':
            self.logger.debug(f"Insufficient data for {url}: laptop_name='{laptop_name}', brand_name='{brand_name}'")
            return None
        
        # Extract all specifications
        price_info = self._extract_price_info(product_data.get('Giá', {}))
        cpu_info = self._extract_cpu_info(product_data.get('Bộ xử lý', {}))
        memory_info = self._extract_memory_storage_info(product_data.get('Bộ nhớ RAM, Ổ cứng', {}))
        display_info = self._extract_display_info(product_data.get('Màn hình', {}))
        graphics_audio_info = self._extract_graphics_audio_info(product_data.get('Đồ họa và Âm thanh', {}))
        connectivity_info = self._extract_connectivity_info(product_data.get('Cổng kết nối & tính năng mở rộng', {}))
        physical_info = self._extract_physical_info(product_data.get('Kích thước - Khối lượng - Pin', {}))
        
        return {
            'basic': {
                'name': laptop_name,
                'description': description,
                'brand': brand_name,
                'url': product_url
            },
            'price': price_info,
            'cpu': cpu_info,
            'memory': memory_info,
            'display': display_info,
            'graphics_audio': graphics_audio_info,
            'connectivity': connectivity_info,
            'physical': physical_info
        }
    
    def _extract_price_info(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract price information"""
        if not isinstance(price_data, dict):
            return {}
        
        current_price = 0.0
        if price_data.get('Giá trị'):
            current_price = float(price_data.get('Giá trị', 0) * 1000000)
        
        return {
            'current_price': current_price,
            'current_price_text': str(price_data.get('Giá hiện tại', '')),
            'original_price_text': str(price_data.get('Giá cũ', '')),
            'discount_percentage_text': str(price_data.get('Phần trăm giảm', '')),
            'price_segment': price_data.get('Phân khúc', 'Unknown'),
            'price_tag': price_data.get('Tag', 'Unknown')
        }
    
    def _extract_cpu_info(self, cpu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract CPU information"""
        if not cpu_data:
            return {}
        
        cpu_model = cpu_data.get('Công nghệ CPU:', ['Unknown'])[0] if cpu_data.get('Công nghệ CPU:') else 'Unknown'
        cpu_cores = 0
        cpu_threads = 0
        cpu_base_speed_ghz = 0.0
        cpu_max_speed_text = ""
        
        try:
            cpu_cores = int(cpu_data.get('Số nhân:', ['0'])[0]) if cpu_data.get('Số nhân:') else 0
            cpu_threads = int(cpu_data.get('Số luồng:', ['0'])[0]) if cpu_data.get('Số luồng:') else 0
            
            speed_text = cpu_data.get('Tốc độ CPU:', [''])[0]
            if speed_text:
                speed_match = re.search(r'(\d+\.?\d*)', speed_text)
                if speed_match:
                    cpu_base_speed_ghz = float(speed_match.group(1))
            
            cpu_max_speed_text = cpu_data.get('Tốc độ tối đa:', [''])[0]
        except:
            pass
        
        return {
            'model': cpu_model,
            'cores': cpu_cores,
            'threads': cpu_threads,
            'base_speed_ghz': cpu_base_speed_ghz,
            'max_speed_text': cpu_max_speed_text
        }
    
    def _extract_memory_storage_info(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract RAM and storage information"""
        if not memory_data:
            return {}
        
        ram_size_gb = 0
        ram_bus_speed_mhz = 0
        storage_capacity_gb = 0
        storage_type = "Unknown"
        storage_interface = "Unknown"
        
        ram_text = memory_data.get('RAM:', [''])[0]
        ram_type = memory_data.get('Loại RAM:', ['Unknown'])[0]
        ram_speed_text = memory_data.get('Tốc độ Bus RAM:', [''])[0]
        ram_max_support_text = memory_data.get('Hỗ trợ RAM tối đa:', [''])[0]
        storage_text = memory_data.get('Ổ cứng:', [''])[0]
        
        try:
            if ram_text:
                ram_match = re.search(r'(\d+)', ram_text)
                if ram_match:
                    ram_size_gb = int(ram_match.group(1))
            
            if ram_speed_text:
                speed_match = re.search(r'(\d+)', ram_speed_text)
                if speed_match:
                    ram_bus_speed_mhz = int(speed_match.group(1))
            
            if storage_text:
                # Extract capacity
                capacity_match = re.search(r'(\d+)\s*GB', storage_text)
                if capacity_match:
                    storage_capacity_gb = int(capacity_match.group(1))
                
                # Determine type and interface
                if 'SSD' in storage_text:
                    storage_type = 'SSD'
                elif 'HDD' in storage_text:
                    storage_type = 'HDD'
                
                if 'NVMe' in storage_text:
                    storage_interface = 'NVMe PCIe'
                elif 'SATA' in storage_text:
                    storage_interface = 'SATA'
        except:
            pass
        
        return {
            'ram_size_gb': ram_size_gb,
            'ram_type': ram_type,
            'ram_bus_speed_mhz': ram_bus_speed_mhz,
            'ram_max_support_text': ram_max_support_text,
            'storage_capacity_gb': storage_capacity_gb,
            'storage_type': storage_type,
            'storage_interface': storage_interface,
            'storage_text': storage_text
        }
    
    def _extract_display_info(self, display_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract display information"""
        if not display_data:
            return {}
        
        screen_size_inches = 0.0
        screen_refresh_rate_hz = 60
        screen_brightness_nits = 0
        
        screen_size_text = display_data.get('Màn hình:', [''])[0]
        screen_resolution_text = display_data.get('Độ phân giải:', ['Unknown'])[0]
        refresh_rate_text = display_data.get('Tần số quét:', ['60Hz'])[0]
        screen_color_gamut = display_data.get('Độ phủ màu:', [''])[0]
        screen_technologies = display_data.get('Công nghệ màn hình:', [])
        
        try:
            # Extract screen size
            size_match = re.search(r'(\d+\.?\d*)', screen_size_text)
            if size_match:
                screen_size_inches = float(size_match.group(1))
            
            # Extract refresh rate
            refresh_match = re.search(r'(\d+)', refresh_rate_text)
            if refresh_match:
                screen_refresh_rate_hz = int(refresh_match.group(1))
            
            # Extract brightness from screen technologies
            for tech in screen_technologies:
                if 'nits' in tech:
                    brightness_match = re.search(r'(\d+)', tech)
                    if brightness_match:
                        screen_brightness_nits = int(brightness_match.group(1))
        except:
            pass
        
        return {
            'size_inches': screen_size_inches,
            'resolution_text': screen_resolution_text,
            'refresh_rate_hz': screen_refresh_rate_hz,
            'color_gamut': screen_color_gamut,
            'brightness_nits': screen_brightness_nits,
            'technologies': screen_technologies
        }
    
    def _extract_graphics_audio_info(self, graphics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract graphics and audio information"""
        if not graphics_data:
            return {}
        
        gpu_text = graphics_data.get('Card màn hình:', ['Unknown'])[0]
        audio_technology = graphics_data.get('Công nghệ âm thanh:', [''])[0]
        
        gpu_model = gpu_text
        gpu_type = 'integrated' if 'tích hợp' in gpu_text.lower() or 'integrated' in gpu_text.lower() else 'dedicated'
        gpu_vram_gb = 0
        
        # Try to extract VRAM info
        try:
            vram_match = re.search(r'(\d+)\s*GB', gpu_text)
            if vram_match:
                gpu_vram_gb = int(vram_match.group(1))
        except:
            pass
        
        return {
            'gpu_model': gpu_model,
            'gpu_type': gpu_type,
            'gpu_vram_gb': gpu_vram_gb,
            'audio_technology': audio_technology
        }
    
    def _extract_connectivity_info(self, connectivity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract connectivity and features information"""
        if not connectivity_data:
            return {}
        
        return {
            'ports': connectivity_data.get('Cổng giao tiếp:', []),
            'wireless_connectivity': connectivity_data.get('Kết nối không dây:', []),
            'webcam_info': connectivity_data.get('Webcam:', ['Unknown'])[0],
            'keyboard_backlight': connectivity_data.get('Đèn bàn phím:', ['Unknown'])[0],
            'additional_features': connectivity_data.get('Tính năng khác:', [])
        }
    
    def _extract_physical_info(self, physical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract physical specifications"""
        if not physical_data:
            return {}
        
        launch_year = 2023
        launch_year_text = physical_data.get('Thời điểm ra mắt:', ['2023'])[0]
        
        try:
            if launch_year_text:
                year_match = re.search(r'(\d{4})', launch_year_text)
                if year_match:
                    launch_year = int(year_match.group(1))
        except:
            launch_year = 2023
        
        return {
            'dimensions_and_weight': physical_data.get('Kích thước:', [''])[0],
            'material': physical_data.get('Chất liệu:', [''])[0],
            'battery_info': physical_data.get('Thông tin Pin:', [''])[0],
            'os_name': physical_data.get('Hệ điều hành:', ['Unknown'])[0],
            'launch_year': launch_year
        }
    
    def _generate_laptop_queries(self, url: str, laptop_info: Dict[str, Any]) -> List[str]:
        """
        Generate all Cypher queries for a single laptop
        
        Args:
            url: Product URL identifier
            laptop_info: Structured laptop information
            
        Returns:
            List[str]: List of Cypher queries for this laptop
        """
        queries = []
        
        # Clean all data using helper functions
        basic_clean = self._clean_basic_info(laptop_info['basic'])
        price_clean = self._clean_price_info(laptop_info['price'])
        cpu_clean = self._clean_cpu_info(laptop_info['cpu'])
        memory_clean = self._clean_memory_info(laptop_info['memory'])
        display_clean = self._clean_display_info(laptop_info['display'])
        graphics_clean = self._clean_graphics_info(laptop_info['graphics_audio'])
        connectivity_clean = self._clean_connectivity_info(laptop_info['connectivity'])
        physical_clean = self._clean_physical_info(laptop_info['physical'])
        
        # Generate main laptop node queries
        queries.extend(self._generate_main_laptop_queries(url, basic_clean, price_clean, 
                                                         cpu_clean, memory_clean, display_clean, 
                                                         graphics_clean, connectivity_clean, physical_clean))
        
        # Generate relationship queries
        queries.extend(self._generate_relationship_queries(url, basic_clean, price_clean, 
                                                          cpu_clean, graphics_clean, 
                                                          display_clean, connectivity_clean))
        
        return queries
    
    def _clean_basic_info(self, basic_info: Dict[str, Any]) -> Dict[str, str]:
        """Clean basic laptop information"""
        return {
            'name': self._safe_escape(basic_info.get('name', '')),
            'description': self._safe_escape(basic_info.get('description', ''))[:1500],
            'brand': self._safe_escape(basic_info.get('brand', '')),
            'url': self._safe_escape(basic_info.get('url', ''))
        }
    
    def _clean_price_info(self, price_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean price information"""
        return {
            'current_price': self._safe_number(price_info.get('current_price', 0)),
            'current_price_text': self._safe_escape(price_info.get('current_price_text', '')),
            'original_price_text': self._safe_escape(price_info.get('original_price_text', '')),
            'discount_percentage_text': self._safe_escape(price_info.get('discount_percentage_text', '')),
            'price_segment': self._safe_escape(price_info.get('price_segment', '')),
            'price_tag': self._safe_escape(price_info.get('price_tag', ''))
        }
    
    def _clean_cpu_info(self, cpu_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean CPU information"""
        return {
            'model': self._safe_escape(cpu_info.get('model', '')),
            'cores': self._safe_int(cpu_info.get('cores', 0)),
            'threads': self._safe_int(cpu_info.get('threads', 0)),
            'base_speed_ghz': self._safe_number(cpu_info.get('base_speed_ghz', 0)),
            'max_speed_text': self._safe_escape(cpu_info.get('max_speed_text', ''))
        }
    
    def _clean_memory_info(self, memory_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean memory and storage information"""
        return {
            'ram_size_gb': self._safe_int(memory_info.get('ram_size_gb', 0)),
            'ram_type': self._safe_escape(memory_info.get('ram_type', '')),
            'ram_bus_speed_mhz': self._safe_int(memory_info.get('ram_bus_speed_mhz', 0)),
            'ram_max_support_text': self._safe_escape(memory_info.get('ram_max_support_text', '')),
            'storage_capacity_gb': self._safe_int(memory_info.get('storage_capacity_gb', 0)),
            'storage_type': memory_info.get('storage_type', 'Unknown'),
            'storage_interface': memory_info.get('storage_interface', 'Unknown'),
            'storage_text': self._safe_escape(memory_info.get('storage_text', ''))
        }
    
    def _clean_display_info(self, display_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean display information"""
        return {
            'size_inches': self._safe_number(display_info.get('size_inches', 0)),
            'resolution_text': self._safe_escape(display_info.get('resolution_text', '')),
            'refresh_rate_hz': self._safe_int(display_info.get('refresh_rate_hz', 60)),
            'color_gamut': self._safe_escape(display_info.get('color_gamut', '')),
            'brightness_nits': self._safe_int(display_info.get('brightness_nits', 0)),
            'technologies': display_info.get('technologies', [])
        }
    
    def _clean_graphics_info(self, graphics_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean graphics and audio information"""
        return {
            'gpu_model': self._safe_escape(graphics_info.get('gpu_model', '')),
            'gpu_type': graphics_info.get('gpu_type', 'Unknown'),
            'gpu_vram_gb': self._safe_int(graphics_info.get('gpu_vram_gb', 0)),
            'audio_technology': self._safe_escape(graphics_info.get('audio_technology', ''))
        }
    
    def _clean_connectivity_info(self, connectivity_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean connectivity information"""
        return {
            'ports': connectivity_info.get('ports', []),
            'wireless_connectivity': connectivity_info.get('wireless_connectivity', []),
            'webcam_info': self._safe_escape(connectivity_info.get('webcam_info', '')),
            'keyboard_backlight': self._safe_escape(connectivity_info.get('keyboard_backlight', '')),
            'additional_features': connectivity_info.get('additional_features', [])
        }
    
    def _clean_physical_info(self, physical_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean physical information"""
        return {
            'dimensions_and_weight': self._safe_escape(physical_info.get('dimensions_and_weight', '')),
            'material': self._safe_escape(physical_info.get('material', '')),
            'battery_info': self._safe_escape(physical_info.get('battery_info', '')),
            'os_name': self._safe_escape(physical_info.get('os_name', '')),
            'launch_year': self._safe_int(physical_info.get('launch_year', 2023))
        }
    
    def _generate_main_laptop_queries(self, url: str, basic_clean: Dict, price_clean: Dict,
                                     cpu_clean: Dict, memory_clean: Dict, display_clean: Dict,
                                     graphics_clean: Dict, connectivity_clean: Dict, 
                                     physical_clean: Dict) -> List[str]:
        """Generate main laptop node property queries"""
        queries = []
        
        # Basic laptop properties
        laptop_basic_query = f"""MERGE (l:Laptop {{productId: '{url}'}}) 
SET l.name = '{basic_clean['name']}', 
    l.url = '{basic_clean['url']}', 
    l.description = '{basic_clean['description']}', 
    l.launchYear = {physical_clean['launch_year']},
    l.currentPrice = {price_clean['current_price']},
    l.currentPriceText = '{price_clean['current_price_text']}',
    l.originalPriceText = '{price_clean['original_price_text']}',
    l.discountPercentageText = '{price_clean['discount_percentage_text']}'"""
        queries.append(laptop_basic_query)
        
        # CPU properties
        cpu_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.cpuModel = '{cpu_clean['model']}',
    l.cpuCores = {cpu_clean['cores']},
    l.cpuThreads = {cpu_clean['threads']},
    l.cpuBaseSpeedGHz = {cpu_clean['base_speed_ghz']},
    l.cpuMaxSpeedText = '{cpu_clean['max_speed_text']}'"""
        queries.append(cpu_query)
        
        # RAM and Storage properties
        memory_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.ramSizeGB = {memory_clean['ram_size_gb']},
    l.ramType = '{memory_clean['ram_type']}',
    l.ramBusSpeedMHz = {memory_clean['ram_bus_speed_mhz']},
    l.ramMaxSupportText = '{memory_clean['ram_max_support_text']}',
    l.storageCapacityGB = {memory_clean['storage_capacity_gb']},
    l.storageType = '{memory_clean['storage_type']}',
    l.storageInterface = '{memory_clean['storage_interface']}',
    l.storageText = '{memory_clean['storage_text']}'"""
        queries.append(memory_query)
        
        # Display properties
        screen_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.screenSizeInches = {display_clean['size_inches']},
    l.screenResolutionText = '{display_clean['resolution_text']}',
    l.screenRefreshRateHz = {display_clean['refresh_rate_hz']},
    l.screenColorGamut = '{display_clean['color_gamut']}',
    l.screenBrightnessNits = {display_clean['brightness_nits']}"""
        queries.append(screen_query)
        
        # Graphics and Audio properties
        graphics_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.gpuModel = '{graphics_clean['gpu_model']}',
    l.gpuType = '{graphics_clean['gpu_type']}',
    l.gpuVramGB = {graphics_clean['gpu_vram_gb']},
    l.audioTechnology = '{graphics_clean['audio_technology']}'"""
        queries.append(graphics_query)
        
        # Connectivity and Features properties
        connectivity_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.webcamInfo = '{connectivity_clean['webcam_info']}',
    l.keyboardBacklight = '{connectivity_clean['keyboard_backlight']}'"""
        queries.append(connectivity_query)
        
        # Physical properties
        physical_query = f"""MATCH (l:Laptop {{productId: '{url}'}}) 
SET l.dimensionsAndWeight = '{physical_clean['dimensions_and_weight']}',
    l.material = '{physical_clean['material']}',
    l.batteryInfo = '{physical_clean['battery_info']}',
    l.os = '{physical_clean['os_name']}'"""
        queries.append(physical_query)
        
        return queries
    
    def _generate_relationship_queries(self, url: str, basic_clean: Dict, price_clean: Dict,
                                      cpu_clean: Dict, graphics_clean: Dict, display_clean: Dict,
                                      connectivity_clean: Dict) -> List[str]:
        """Generate relationship queries for nodes and connections"""
        queries = []
        
        # Create Brand and relationship
        if basic_clean['brand']:
            brand_query = f"MERGE (b:Brand {{name: '{basic_clean['brand']}'}}) WITH b MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:MANUFACTURED_BY]->(b)"
            queries.append(brand_query)
        
        # Create PriceSegment and relationship
        if price_clean['price_segment'] and price_clean['price_segment'] != 'Unknown':
            price_segment_query = f"MERGE (ps:PriceSegment {{name: '{price_clean['price_segment']}'}}) WITH ps MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:IN_PRICE_SEGMENT]->(ps)"
            queries.append(price_segment_query)
        
        # Create PriceTag and relationship
        if price_clean['price_tag'] and price_clean['price_tag'] != 'Unknown':
            price_tag_query = f"MERGE (pt:PriceTag {{name: '{price_clean['price_tag']}'}}) WITH pt MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_PRICE_TAG]->(pt)"
            queries.append(price_tag_query)
        
        # Create CPU node and relationship
        if cpu_clean['model'] and cpu_clean['model'] != 'Unknown':
            cpu_node_query = f"""MERGE (c:CPU {{modelName: '{cpu_clean['model']}'}}) 
SET c.cores = {cpu_clean['cores']},
    c.threads = {cpu_clean['threads']},
    c.baseSpeedGHz = {cpu_clean['base_speed_ghz']},
    c.maxSpeedText = '{cpu_clean['max_speed_text']}'
WITH c MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_CPU]->(c)"""
            queries.append(cpu_node_query)
        
        # Create GPU node and relationship
        if graphics_clean['gpu_model'] and graphics_clean['gpu_model'] != 'Unknown':
            gpu_node_query = f"""MERGE (g:GraphicsCard {{modelName: '{graphics_clean['gpu_model']}'}}) 
SET g.type = '{graphics_clean['gpu_type']}'"""
            if graphics_clean['gpu_vram_gb'] > 0:
                gpu_node_query += f", g.vramGB = {graphics_clean['gpu_vram_gb']}"
            gpu_node_query += f" WITH g MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_GRAPHICS_CARD]->(g)"
            queries.append(gpu_node_query)
        
        # Create display technology nodes and relationships
        if isinstance(display_clean['technologies'], list):
            for tech in display_clean['technologies']:
                if tech and tech.strip():
                    tech_clean = self._safe_escape(tech.strip())
                    if tech_clean:
                        display_tech_query = f"MERGE (dt:DisplayTechnology {{name: '{tech_clean}'}}) WITH dt MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_DISPLAY_TECHNOLOGY]->(dt)"
                        queries.append(display_tech_query)
        
        # Create port nodes and relationships
        if isinstance(connectivity_clean['ports'], list):
            for port in connectivity_clean['ports']:
                if port and port.strip():
                    port_clean = self._safe_escape(port.strip())
                    if port_clean:
                        port_query = f"MERGE (p:Port {{name: '{port_clean}'}}) WITH p MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_PORT]->(p)"
                        queries.append(port_query)
        
        # Create wireless connectivity nodes and relationships
        if isinstance(connectivity_clean['wireless_connectivity'], list):
            for wireless in connectivity_clean['wireless_connectivity']:
                if wireless and wireless.strip():
                    wireless_clean = self._safe_escape(wireless.strip())
                    if wireless_clean:
                        wireless_query = f"MERGE (w:WirelessConnectivity {{name: '{wireless_clean}'}}) WITH w MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:SUPPORTS_WIRELESS]->(w)"
                        queries.append(wireless_query)
        
        # Create feature nodes and relationships
        if isinstance(connectivity_clean['additional_features'], list):
            for feature in connectivity_clean['additional_features']:
                if feature and feature.strip():
                    feature_clean = self._safe_escape(feature.strip())
                    if feature_clean:
                        feature_query = f"MERGE (f:Feature {{name: '{feature_clean}'}}) WITH f MATCH (l:Laptop {{productId: '{url}'}}) MERGE (l)-[:HAS_FEATURE]->(f)"
                        queries.append(feature_query)
        
        return queries
    
    def _save_cypher_queries(self, queries: List[str], output_file: str) -> None:
        """
        Save Cypher queries to file
        
        Args:
            queries: List of Cypher queries
            output_file: Path to output file
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for query in queries:
                if query.strip():  # Only write non-empty queries
                    # Normalize the query to a single line by replacing line breaks with spaces
                    # and removing extra whitespace
                    normalized_query = ' '.join(query.strip().split())
                    f.write(normalized_query + '\n')
    
    # Helper methods for data cleaning and validation
    def _safe_escape(self, text: Any) -> str:
        """Safely escape text for Cypher queries"""
        if not text or text == "Unknown" or text == "":
            return ""
        # Replace special characters with their escaped versions
        text = str(text)
        text = text.replace("\\", "\\\\")  # Escape backslash first
        text = text.replace("'", "\\'")    # Escape single quotes
        text = text.replace('"', '\\"')    # Escape double quotes
        text = text.replace('\n', ' ')     # Replace newlines with spaces
        text = text.replace('\r', ' ')     # Replace carriage returns with spaces
        text = text.replace('\t', ' ')     # Replace tabs with spaces
        return text
    
    def _safe_number(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to number"""
        try:
            return float(value) if value else default
        except:
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to integer"""
        try:
            return int(value) if value else default
        except:
            return default 