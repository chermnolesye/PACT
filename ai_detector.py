import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM
)
import numpy as np
from typing import Dict, Tuple, List
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIDetector:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Используется устройство: {self.device}")
        
        self.perplexity_models = {}
        self._load_models()
        
        self.perplexity_thresholds = {
            'french': 65,
            'german': 60,
            'multilingual': 70
        }
    
    def _load_models(self):
        """Загрузка специализированных моделей для каждого языка"""
        try:
            logger.info("Загрузка специализированных моделей для перплексии...")
            
            models_config = {
                'french': "dbddv01/gpt2-french-small",
                'german': "stefan-it/german-gpt2-larger",
                'multilingual': "gpt2"
            }
            
            for lang, model_name in models_config.items():
                logger.info(f"Загрузка модели для {lang}: {model_name}")
                
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_name)
                    model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device)
                    
                    if tokenizer.pad_token is None:
                        tokenizer.pad_token = tokenizer.eos_token
                        
                    self.perplexity_models[lang] = {
                        'tokenizer': tokenizer, 
                        'model': model
                    }
                    
                    logger.info(f"Модель для {lang} успешно загружена")
                    
                except Exception as e:
                    logger.error(f"Ошибка загрузки модели {model_name}: {e}")
                    logger.info(f"Использую универсальную GPT-2 для {lang}")
                    
                    # Запасной вариант
                    tokenizer = AutoTokenizer.from_pretrained("gpt2")
                    model = AutoModelForCausalLM.from_pretrained("gpt2").to(self.device)
                    
                    if tokenizer.pad_token is None:
                        tokenizer.pad_token = tokenizer.eos_token
                        
                    self.perplexity_models[lang] = {
                        'tokenizer': tokenizer, 
                        'model': model
                    }
            
            logger.info("Все модели успешно загружены")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при загрузке моделей: {e}")
            raise
    
    def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        text_lower = text.lower()
        
        french_indicators = [
            'le', 'la', 'les', 'de', 'et', 'est', 'que', 'dans', 'pour', 
            'il', 'elle', 'nous', 'vous', 'des', 'un', 'une', 'au', 'aux',
            'avec', 'son', 'ses', 'sur', 'par', 'pas', 'plus', 'tout', 'mon'
        ]
        
        german_indicators = [
            'der', 'die', 'das', 'und', 'ist', 'zu', 'sie', 'wir', 'ich', 
            'du', 'nicht', 'mit', 'von', 'den', 'dem', 'des', 'ein', 'eine',
            'auf', 'für', 'sich', 'auch', 'aus', 'hat', 'sind', 'bin'
        ]
        
        french_score = sum(1 for word in french_indicators if word in text_lower)
        german_score = sum(1 for word in german_indicators if word in text_lower)
        
        french_chars = len(re.findall(r'[àâäèéêëîïôùûüç]', text))
        german_chars = len(re.findall(r'[äöüß]', text))
    
        french_score += french_chars * 3
        german_score += german_chars * 3

        logger.info(f"Французский счет: {french_score}, Немецкий счет: {german_score}")
        
        if french_score > german_score and french_score >= 2:
            return 'french'
        elif german_score > french_score and german_score >= 2:
            return 'german'
        else:
            return 'multilingual'
    
    def calculate_perplexity(self, text: str, language: str) -> float:
        """Расчет перплексии с использованием специализированной модели"""
        try:
            if language not in self.perplexity_models:
                language = 'multilingual'
                
            model_info = self.perplexity_models[language]
            tokenizer = model_info['tokenizer']
            model = model_info['model']
            
            inputs = tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=1024,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = model(**inputs, labels=inputs['input_ids'])
                loss = outputs.loss
                
                if loss is not None:
                    perplexity = torch.exp(loss).item()
                    if perplexity > 10000 or perplexity < 1:
                        perplexity = 1000.0
                else:
                    perplexity = 1000.0
                    
            return perplexity
            
        except Exception as e:
            logger.error(f"Ошибка при расчете перплексии: {e}")
            return 1000.0
    
    def statistical_analysis(self, text: str) -> float:
        """Статистический анализ текста"""
        try:
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            words = re.findall(r'\b\w+\b', clean_text.lower())
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if len(words) < 5 or len(sentences) < 1:
                return 0.3

            unique_words = len(set(words))
            lexical_diversity = unique_words / len(words)
            avg_sentence_length = len(words) / len(sentences)
            avg_word_length = np.mean([len(word) for word in words]) if words else 0

            word_freq = {}
            for word in words:
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
            max_repetition = max(word_freq.values()) if word_freq else 1

            sentence_lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
            sentence_variance = np.var(sentence_lengths) if len(sentence_lengths) > 1 else 0

            if len(sentence_lengths) > 2:
                mean_len = np.mean(sentence_lengths)
                normalized_variance = sentence_variance / (mean_len ** 2) if mean_len > 0 else 0
                uniformity_score = 1 - min(normalized_variance * 5, 1.0)
            else:
                uniformity_score = 0.5

            ai_score = (
                0.30 * (1 - lexical_diversity) +
                0.10 * min(avg_sentence_length / 30, 1) +
                0.15 * min(avg_word_length / 8, 1) +
                0.20 * min(max_repetition / 3, 1) +
                0.25 * uniformity_score
            )

            return max(0.1, min(0.9, ai_score))

        except Exception as e:
            logger.error(f"Ошибка в статистическом анализе: {e}")
            return 0.5
    
    def analyze_text(self, text: str) -> Dict:
        """Основной метод анализа текста"""
        if not text or len(text.strip()) < 10:
            return {
                'error': 'Текст слишком короткий для анализа',
                'is_ai': False,
                'confidence': 0.0,
                'language': 'unknown'
            }
        
        try:
            language = self.detect_language(text)
            perplexity = self.calculate_perplexity(text, language)
            statistical_confidence = self.statistical_analysis(text)
            
            threshold = self.perplexity_thresholds.get(language, 70)
            
            if perplexity < threshold * 0.5:
                perplexity_confidence = 0.9
            elif perplexity < threshold * 0.8:
                perplexity_confidence = 0.7
            elif perplexity < threshold:
                perplexity_confidence = 0.5
            elif perplexity < threshold * 1.5:
                perplexity_confidence = 0.3
            else:
                perplexity_confidence = 0.1
            
            logger.info(f"Перплексия: {perplexity:.2f}, уверенность в AI: {perplexity_confidence:.2f}")
            logger.info(f"Статистическая уверенность в AI: {statistical_confidence:.2f}")
            
            total_confidence = (perplexity_confidence * 0.8 + statistical_confidence * 0.2)
            is_ai_combined = total_confidence > 0.5
            
            result = {
                'is_ai': bool(is_ai_combined),
                'confidence': float(total_confidence),
                'language': language,
                'perplexity': float(perplexity),
                'model_used': f"Специализированная модель для {language}",
                'details': {
                    'statistical_confidence': float(statistical_confidence),
                    'perplexity_confidence': float(perplexity_confidence),
                    'text_length': len(text),
                    'word_count': len(re.findall(r'\b\w+\b', text.lower()))
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе текста: {e}")
            return {
                'error': str(e),
                'is_ai': False,
                'confidence': 0.0,
                'language': 'unknown'
            }

_ai_detector_instance = None

def get_ai_detector():
    global _ai_detector_instance
    if _ai_detector_instance is None:
        _ai_detector_instance = AIDetector()
    return _ai_detector_instance
