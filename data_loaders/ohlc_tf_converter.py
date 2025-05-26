import pandas as pd
from pathlib import Path
import logging
from typing import List, Dict

class OHLCTimeframeConverter:
    def __init__(self, data_directory: str = "data"):
        self.data_directory = Path(data_directory)
        self.supported_timeframes = {
            '4H': {'hours': 4, 'rule': '4H'},
            'D': {'hours': 24, 'rule': 'D'},
            'W': {'hours': 168, 'rule': 'W-MON'}
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_hourly_data(self, csv_file_path: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(csv_file_path)
            
            df['time'] = pd.to_datetime(df['time'])
            
            df.set_index('time', inplace=True)
            
            required_columns = ['open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")
            
            df.sort_index(inplace=True)
            
            self.logger.info(f"Loaded {len(df)} hourly records from {csv_file_path}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data from {csv_file_path}: {str(e)}")
            raise
    
    def resample_ohlc(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if timeframe not in self.supported_timeframes:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(self.supported_timeframes.keys())}")
        
        rule = self.supported_timeframes[timeframe]['rule']
        
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        self.logger.info(f"Resampled to {timeframe}: {len(resampled)} records")
        return resampled
    
    def save_resampled_data(self, df: pd.DataFrame, output_path: str) -> None:
        try:
            df_to_save = df.reset_index()
            df_to_save.to_csv(output_path, index=False)
            self.logger.info(f"Saved resampled data to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving data to {output_path}: {str(e)}")
            raise
    
    def process_single_file(self, input_file: str, timeframes: List[str] = None) -> Dict[str, str]:
        if timeframes is None:
            timeframes = ['4H', 'D', 'W']
        
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        hourly_data = self.load_hourly_data(input_file)
        
        output_files = {}
        
        for tf in timeframes:
            try:
                resampled_data = self.resample_ohlc(hourly_data, tf)
                
                base_name = input_path.stem.replace('_1h', '')
                output_filename = f"{base_name}_{tf.lower()}.csv"
                output_path = input_path.parent / output_filename
                
                self.save_resampled_data(resampled_data, str(output_path))
                output_files[tf] = str(output_path)
                
            except Exception as e:
                self.logger.error(f"Error processing {tf} timeframe for {input_file}: {str(e)}")
                continue
        
        return output_files
    
    def process_directory(self, pattern: str = "*_1h.csv", timeframes: List[str] = None) -> Dict[str, Dict[str, str]]:
        if timeframes is None:
            timeframes = ['4H', 'D', 'W']
        
        csv_files = list(self.data_directory.glob(pattern))
        
        if not csv_files:
            self.logger.warning(f"No files found matching pattern: {pattern} in {self.data_directory}")
            return {}
        
        results = {}
        
        for csv_file in csv_files:
            self.logger.info(f"Processing {csv_file.name}...")
            try:
                output_files = self.process_single_file(str(csv_file), timeframes)
                results[str(csv_file)] = output_files
                
            except Exception as e:
                self.logger.error(f"Failed to process {csv_file}: {str(e)}")
                continue
        
        return results
    
    def process_nested_directories(self, pattern: str = "*_1h.csv", timeframes: List[str] = None) -> Dict[str, Dict[str, Dict[str, str]]]:
        if timeframes is None:
            timeframes = ['4H', 'D', 'W']
        
        if not self.data_directory.exists():
            self.logger.error(f"Data directory does not exist: {self.data_directory}")
            return {}
        
        results = {}
        
        subdirectories = [d for d in self.data_directory.iterdir() if d.is_dir()]
        
        if not subdirectories:
            self.logger.warning(f"No subdirectories found in {self.data_directory}")
            return {"root": self.process_directory(pattern, timeframes)}
        
        self.logger.info(f"Found {len(subdirectories)} commodity folders: {[d.name for d in subdirectories]}")
        
        for commodity_folder in subdirectories:
            commodity_name = commodity_folder.name
            self.logger.info(f"\n=== Processing {commodity_name.upper()} ===")
            
            csv_files = list(commodity_folder.glob(pattern))
            
            if not csv_files:
                self.logger.warning(f"No files matching '{pattern}' found in {commodity_folder}")
                continue
            
            commodity_results = {}
            
            for csv_file in csv_files:
                self.logger.info(f"Processing {csv_file.name} in {commodity_name} folder...")
                try:
                    output_files = self.process_single_file(str(csv_file), timeframes)
                    commodity_results[str(csv_file)] = output_files
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {csv_file}: {str(e)}")
                    continue
            
            if commodity_results:
                results[commodity_name] = commodity_results
        
        return results
    
    def process_all_commodities(self, timeframes: List[str] = None) -> Dict[str, Dict[str, Dict[str, str]]]:
        if timeframes is None:
            timeframes = ['4H', 'D', 'W']
        
        self.logger.info(f"Starting automatic processing of all commodities...")
        self.logger.info(f"Target timeframes: {timeframes}")
        
        patterns_to_try = ["*_1h.csv", "*1h.csv", "*_1H.csv", "*1H.csv"]
        
        results = {}
        
        for pattern in patterns_to_try:
            self.logger.info(f"Trying pattern: {pattern}")
            temp_results = self.process_nested_directories(pattern, timeframes)
            
            if temp_results:
                for commodity, files in temp_results.items():
                    if files:
                        if commodity not in results:
                            results[commodity] = files
                        else:
                            results[commodity].update(files)
        
        if not results:
            self.logger.warning("No 1-hour CSV files found in any commodity folders")
            
        return results
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        validation_results = {
            'total_records': len(df),
            'missing_data': df.isnull().sum().to_dict(),
            'invalid_ohlc': 0,
            'gaps_in_data': [],
            'data_range': {
                'start': df.index.min(),
                'end': df.index.max()
            }
        }
        
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )
        validation_results['invalid_ohlc'] = invalid_ohlc.sum()
        
        time_diffs = df.index.to_series().diff()
        large_gaps = time_diffs[time_diffs > pd.Timedelta(hours=2)]
        validation_results['gaps_in_data'] = large_gaps.index.tolist()
        
        return validation_results

def main():
    converter = OHLCTimeframeConverter(data_directory="../data")
    
    results = converter.process_all_commodities(timeframes=['4H', 'D', 'W'])
    
    print("\n" + "="*60)
    print("           OHLC PROCESSING SUMMARY")
    print("="*60)
    
    total_files_processed = 0
    total_outputs_generated = 0
    
    for commodity, files_dict in results.items():
        print(f"\n📁 {commodity.upper()} COMMODITY:")
        print("-" * 40)
        
        commodity_files = 0
        commodity_outputs = 0
        
        for input_file, output_files in files_dict.items():
            input_filename = Path(input_file).name
            print(f"  📄 Input: {input_filename}")
            
            commodity_files += 1
            
            for timeframe, output_path in output_files.items():
                output_filename = Path(output_path).name
                print(f"    ⏰ {timeframe}: {output_filename}")
                commodity_outputs += 1
        
        total_files_processed += commodity_files
        total_outputs_generated += commodity_outputs
        
        print(f"  📊 Files processed: {commodity_files}")
        print(f"  📈 Outputs generated: {commodity_outputs}")
    
    print("\n" + "="*60)
    print(f"🎯 TOTAL FILES PROCESSED: {total_files_processed}")
    print(f"🎯 TOTAL OUTPUTS GENERATED: {total_outputs_generated}")
    print("="*60)
    
    if not results:
        print("\n⚠️  No files were processed. Please check:")
        print("   - Data directory exists and contains commodity folders")
        print("   - Commodity folders contain *_1h.csv files")
        print("   - CSV files have the correct format (time, open, high, low, close)")

def process_specific_commodities(commodities: List[str], timeframes: List[str] = None):
    if timeframes is None:
        timeframes = ['4H', 'D', 'W']
    
    converter = OHLCTimeframeConverter(data_directory="data")
    
    for commodity in commodities:
        commodity_path = Path("data") / commodity
        if not commodity_path.exists():
            print(f"⚠️  Commodity folder '{commodity}' not found")
            continue
        
        print(f"\n🔄 Processing {commodity.upper()}...")
        
        original_data_dir = converter.data_directory
        converter.data_directory = commodity_path
        
        results = converter.process_directory(timeframes=timeframes)
        
        converter.data_directory = original_data_dir
        
        if results:
            print(f"✅ {commodity.upper()}: {len(results)} files processed")
        else:
            print(f"❌ {commodity.upper()}: No files processed")

if __name__ == "__main__":
    main()