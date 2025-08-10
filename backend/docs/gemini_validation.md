# Gemini RAG Validation Layer

## Overview

The Gemini Validation Layer is an enhancement to the FinDocGPT RAG system that addresses the issue of poor RAG accuracy and limited content coverage. It adds an intelligent validation step that:

1. **Validates RAG responses** using Gemini to determine if they adequately answer user queries
2. **Enhances responses** with internet search when RAG validation fails
3. **Provides source attribution** so the system knows whether information came from documents or web search

## Architecture

```
User Query → RAG System → Gemini Validation → Enhanced Response
                ↓              ↓
            RAG Response   Validation Failed?
                ↓              ↓
            Return RAG     Gemini Search → Return Enhanced
```

## How It Works

### 1. RAG Query Execution
- The system first executes the normal RAG query against the document database
- This returns the standard RAG response based on available documents

### 2. Gemini Validation
- The RAG query and response are sent to Gemini for evaluation
- Gemini assesses whether the response adequately answers the question
- Evaluation criteria include:
  - Does the response directly address the question?
  - Is the information relevant and specific?
  - Are there significant gaps or missing information?
  - Is the response substantive enough to be helpful?

### 3. Enhancement (if needed)
- If validation fails, Gemini uses its built-in search capabilities with strict source requirements
- The search emphasizes TRUSTED FINANCIAL SOURCES ONLY:
  * Official company filings (SEC, 10-K, 10-Q, 8-K reports)
  * Reputable financial news (Reuters, Bloomberg, WSJ, Financial Times)
  * Government agencies (Federal Reserve, Treasury, SEC, BLS)
  * Established data providers (Yahoo Finance, MarketWatch)
  * Major investment banks and research firms
  * Credit rating agencies (Moody's, S&P, Fitch)
- Quality assessment validates source reliability and data completeness
- The web-based response replaces or supplements the RAG response

### 4. Source Attribution
- All responses include metadata indicating their source:
  - `"source": "rag"` - Information from documents
  - `"source": "gemini_search"` - Information from web search
- This allows the iterative analysis to make informed decisions

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Gemini API Key (get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# Alternative variable name (either works)
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Installation

The required package is already included in `requirements.txt`:

```bash
pip install google-genai
```

## Usage

### Automatic Integration

The validation layer is automatically integrated into the RAG pipeline. No code changes are needed for existing functionality.

### Response Structure

Enhanced RAG responses now include additional metadata:

```python
{
    'query': 'What is Apple\'s revenue growth?',
    'results': ['Enhanced response text...'],
    'original_rag_results': ['Original RAG response...'],
    'validation_result': {
        'validation_passed': False,
        'reasoning': 'Response lacks specific financial data',
        'confidence_score': 0.3,
        'enhanced_response': {
            'search_available': True,
            'response': 'Apple reported 15% revenue growth...',
            'source': 'gemini_search'
        }
    },
    'source': 'gemini_search',
    'timestamp': '2024-01-01T12:00:00'
}
```

## Testing

Run the test script to verify the integration:

```bash
cd backend
python test_gemini_validation.py
```

This will test:
- Poor RAG responses that trigger enhancement
- Good RAG responses that pass validation
- Direct Gemini search functionality

## Benefits

### 1. Improved Accuracy
- Validates RAG responses before sending to analysis
- Reduces hallucinations and irrelevant information
- Strict financial information quality standards

### 2. Enhanced Coverage with Trusted Sources
- Uses web search to fill gaps in document knowledge
- **ONLY uses trusted financial sources** (SEC filings, Bloomberg, Reuters, etc.)
- Provides current information not available in documents
- Quality assessment ensures financial data reliability

### 3. Source Transparency
- Clear attribution of information sources
- Quality indicators for financial data standards
- Allows analysis to weight information appropriately
- Warnings when data quality may be insufficient

### 4. Graceful Fallback
- Falls back to original RAG if Gemini is unavailable
- Robust error handling prevents system failures
- Quality warnings when search results don't meet financial standards

## Configuration Options

### Disabling Validation

To disable Gemini validation (fallback to RAG-only):

```python
# In your service initialization
validation_service = GeminiValidationService()
validation_service.validation_enabled = False
```

### Validation Strictness

The validation prompt can be adjusted in `GeminiValidationService.validate_rag_response()` to be more or less strict based on your needs.

## Monitoring

The service logs validation decisions and search usage:

```
INFO: Validation result for query 'What is Apple's revenue...': False
INFO: RAG validation failed for query: What is Apple's revenue... - searching with Gemini
INFO: Gemini search completed for query: What is Apple's revenue...
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure `GEMINI_API_KEY` is set in your environment
   - Check that the API key is valid and has proper permissions

2. **Import Errors**
   - Verify `google-genai` package is installed
   - Check Python environment and package versions

3. **Validation Always Passes**
   - Check API key permissions
   - Review validation prompt strictness
   - Verify Gemini model availability

### Error Handling

The service gracefully handles errors:
- Invalid API keys → Falls back to RAG-only mode
- Network issues → Returns original RAG response
- Parsing errors → Logs error and continues with RAG

## Future Enhancements

Potential improvements to consider:

1. **Caching** - Cache validation results for repeated queries
2. **Custom Models** - Support for different Gemini model versions
3. **Hybrid Responses** - Combine RAG and search results intelligently
4. **Confidence Thresholds** - Configurable validation strictness
5. **Usage Analytics** - Track validation success rates and search usage
