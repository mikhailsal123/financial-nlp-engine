from src.analysis.deep_analysis_engine import DeepAnalysisEngine

engine = DeepAnalysisEngine()
profile = {
    'name': 'Apple Inc',
    'description': 'Apple makes iPhone, Apple Pay and Apple Watch. CEO Tim Cook leads product innovation.'
}
kw, strong = engine._build_dynamic_keywords('AAPL', profile)
print('KW sample:', kw[:20])
print('Strong:', strong)
