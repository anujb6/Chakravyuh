import talib
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from PyQt5.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QLabel, QSpinBox
from PyQt5.QtCore import pyqtSignal
from lightweight_charts.widgets import QtChart
from lightweight_charts.abstract import Line

class IndicatorManager:
    def __init__(self, chart:QtChart):
        self.chart = chart
        self.indicators = {}
        self.data = None
    
    def clear_all(self):
        """Safely remove all indicators"""
        for name in list(self.indicators.keys()):
            self.remove_indicator(name)

    def set_data(self, data: pd.DataFrame):
        self.data = data.copy(deep=True)
        if not self.data.empty:
            if not pd.api.types.is_datetime64_any_dtype(self.data['time']):
                self.data['time'] = pd.to_datetime(self.data['time'])
            
            if self.data['time'].dt.tz is not None:
                self.data['time'] = self.data['time'].dt.tz_localize(None)
        self.recalculate_all()
    
    def update_data(self, series: pd.Series):
        if self.data is not None:
            series_time = series['time']
            
            if pd.api.types.is_datetime64_any_dtype(series_time):
                if hasattr(series_time, 'tz_localize') and series_time.tz is not None:
                    series_time = series_time.tz_localize(None)
            else:
                series_time = pd.to_datetime(series_time)
                if series_time.tz is not None:
                    series_time = series_time.tz_localize(None)
            
            new_row = pd.DataFrame([{
                'time': series_time,
                'open': series['open'],
                'high': series['high'],
                'low': series['low'],
                'close': series['close']
            }])
            
            if series_time in self.data['time'].values:
                self.data = self.data[self.data['time'] != series_time].copy()
            self.data = pd.concat([self.data, new_row], ignore_index=True)
            self.data = self.data.sort_values('time').reset_index(drop=True)
            
            for name, indicator in self.indicators.items():
                if indicator['type'] == 'bollinger_bands':
                    self._update_bollinger_bands_full(name, indicator)
        
        self.recalculate_all()

    def remove_indicator(self, name: str):
        if name in self.indicators:
            try:
                for line in self.indicators[name]['lines']:
                    try:
                       line.set(None)
                    except Exception as e:
                        print(f"Error deleting line: {e}")
            finally:
                del self.indicators[name]

    def clear_all(self):
        for name in list(self.indicators.keys()):
            self.remove_indicator(name)

    def recalculate_all(self):
        if self.data is None or self.data.empty:
            return
        for name, indicator in list(self.indicators.items()):
            if indicator['type'] == 'bollinger_bands':
                self._update_bollinger_bands_full(name, indicator)

    def _update_bollinger_bands_full(self, name: str, indicator: dict):
        if self.data is None or len(self.data) < 2:
            return
            
        params = indicator['params']
        period = params['period']
        std_dev = params['std_dev']
        
        if len(self.data) < period:
            return
            
        closes = self.data['close'].values
        upper, middle, lower = talib.BBANDS(closes, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        times = self.data['time']
        bb_data = pd.DataFrame({
            'time': times,
            'upper': upper,
            'middle': middle,
            'lower': lower
        }).dropna()
        
        indicator['lines'][0].set(bb_data[['time', 'upper']].rename(columns={'upper': 'value'}))
        indicator['lines'][1].set(bb_data[['time', 'middle']].rename(columns={'middle': 'value'}))
        indicator['lines'][2].set(bb_data[['time', 'lower']].rename(columns={'lower': 'value'}))
        
        indicator['data'] = bb_data

    def add_bollinger_bands(self, period=20, std_dev=2, name="BB"):
        if self.data is None or len(self.data) < period:
            return None
            
        closes = self.data['close'].values
        upper, middle, lower = talib.BBANDS(closes, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        times = self.data['time']
        bb_data = pd.DataFrame({
            'time': times,
            'upper': upper,
            'middle': middle, 
            'lower': lower
        }).dropna()

        upper_line = self.chart.create_line(color='rgba(255, 0, 0, 0.7)', style='solid', width=1, price_line=False, price_label=False)
        middle_line = self.chart.create_line(color='rgba(0, 0, 255, 0.7)', style='dashed', width=1, price_line=False, price_label=False)
        lower_line = self.chart.create_line(color='rgba(255, 0, 0, 0.7)', style='solid', width=1, price_line=False, price_label=False)
        
        upper_line.set(bb_data[['time', 'upper']].rename(columns={'upper': 'value'}))
        middle_line.set(bb_data[['time', 'middle']].rename(columns={'middle': 'value'}))
        lower_line.set(bb_data[['time', 'lower']].rename(columns={'lower': 'value'}))
        
        self.indicators[name] = {
            'type': 'bollinger_bands',
            'lines': [upper_line, middle_line, lower_line],
            'params': {'period': period, 'std_dev': std_dev},
            'data': bb_data
        }
        
        return name

class IndicatorControls:
    indicator_added = pyqtSignal(str)
    indicator_removed = pyqtSignal(str)
    
    def __init__(self, parent_layout):
        self.manager = None
        self.setup_ui(parent_layout)
    
    def set_manager(self, manager: IndicatorManager):
        self.manager = manager
    
    def setup_ui(self, parent_layout):
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(["Bollinger Bands"])
        self.indicator_combo.setMaximumWidth(120)
        
        self.period_spin = QSpinBox()
        self.period_spin.setRange(5, 200)
        self.period_spin.setValue(20)
        self.period_spin.setMaximumWidth(60)
        
        self.std_spin = QSpinBox()
        self.std_spin.setRange(1, 5)
        self.std_spin.setValue(2)
        self.std_spin.setMaximumWidth(40)
        
        self.add_btn = QPushButton("Add")
        self.add_btn.setMaximumWidth(50)
        self.add_btn.clicked.connect(self.add_indicator)
        
        self.remove_combo = QComboBox()
        self.remove_combo.setMaximumWidth(80)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setMaximumWidth(60)
        self.remove_btn.clicked.connect(self.remove_indicator)
        
        parent_layout.addWidget(QLabel("Indicator:"))
        parent_layout.addWidget(self.indicator_combo)
        parent_layout.addWidget(QLabel("Period:"))
        parent_layout.addWidget(self.period_spin)
        parent_layout.addWidget(QLabel("StdDev:"))
        parent_layout.addWidget(self.std_spin)
        parent_layout.addWidget(self.add_btn)
        parent_layout.addWidget(self.remove_combo)
        parent_layout.addWidget(self.remove_btn)
    
    def add_indicator(self):
        if not self.manager:
            return
            
        indicator_type = self.indicator_combo.currentText()
        if indicator_type == "Bollinger Bands":
            period = self.period_spin.value()
            std_dev = self.std_spin.value()
            name = f"BB_{period}_{std_dev}"
            
            result = self.manager.add_bollinger_bands(period, std_dev, name)
            if result:
                self.remove_combo.addItem(name)
    
    def clear_indicators(self):
        """Clear the remove combo box"""
        self.remove_combo.clear()
    
    def remove_indicator(self):
        if not self.manager:
            return
            
        name = self.remove_combo.currentText()
        if name:
            self.manager.remove_indicator(name)
            index = self.remove_combo.findText(name)
            if index >= 0:
                self.remove_combo.removeItem(index)