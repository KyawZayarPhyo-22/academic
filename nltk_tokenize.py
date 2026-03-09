import nltk
import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import get_current_user

router = APIRouter()

class TextInput(BaseModel):
    text: str
    language: str = 'english'

def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove special chars, extra spaces"""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def remove_stopwords(tokens: list, language: str = 'english') -> list:
    """Remove common stopwords from token list"""
    try:
        stop_words = set(stopwords.words(language))
        return [word for word in tokens if word not in stop_words]
    except:
        return tokens

def stem_tokens(tokens: list) -> list:
    """Apply stemming to reduce words to root form"""
    stemmer = PorterStemmer()
    return [stemmer.stem(word) for word in tokens]

def lemmatize_tokens(tokens: list) -> list:
    """Apply lemmatization to reduce words to base form"""
    lemmatizer = WordNetLemmatizer()
    return [lemmatizer.lemmatize(word) for word in tokens]

@router.post('/api/tokenize')
def tokenize_text(data: TextInput, current_user=Depends(get_current_user)):
    """Tokenize text into words"""
    tokens = word_tokenize(data.text)
    return {'tokens': tokens, 'count': len(tokens)}

@router.post('/api/tokenize/sentences')
def tokenize_sentences(data: TextInput, current_user=Depends(get_current_user)):
    """Tokenize text into sentences"""
    sentences = sent_tokenize(data.text)
    return {'sentences': sentences, 'count': len(sentences)}

@router.post('/api/normalize')
def normalize(data: TextInput, current_user=Depends(get_current_user)):
    """Normalize text"""
    normalized = normalize_text(data.text)
    return {'original': data.text, 'normalized': normalized}

@router.post('/api/process')
def process_text(data: TextInput, current_user=Depends(get_current_user)):
    """Complete text processing: normalize, tokenize, remove stopwords, lemmatize"""
    # Normalize
    normalized = normalize_text(data.text)
    
    # Tokenize
    tokens = word_tokenize(normalized)
    
    # Remove stopwords
    filtered_tokens = remove_stopwords(tokens, data.language)
    
    # Lemmatize
    lemmatized = lemmatize_tokens(filtered_tokens)
    
    return {
        'original': data.text,
        'normalized': normalized,
        'tokens': tokens,
        'filtered_tokens': filtered_tokens,
        'lemmatized': lemmatized,
        'token_count': len(tokens),
        'filtered_count': len(filtered_tokens)
    }
