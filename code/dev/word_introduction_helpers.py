import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt

class VocabularyDiffusionDetector:
    def __init__(self, data):
        """
        data should be a DataFrame with columns:
        - year, meetingno, pid, dynamic_income, text, paranum
        """
        self.data = data.sort_values(['year', 'meetingno', 'paranum'])
        self.vocabulary_history = set()
        self.word_introductions = []
        
    def detect_novel_words(self, paragraph_text, min_word_length=3):
        """Find words in paragraph that haven't appeared before"""
        words = set(paragraph_text.lower().split())
        # Filter out very short words and common stopwords
        words = {w for w in words if len(w) >= min_word_length and w.isalpha()}
        
        novel_words = words - self.vocabulary_history
        self.vocabulary_history.update(words)
        
        return novel_words
    
    def track_vocabulary_diffusion(self, inc_cat, lookback_window=50):
        """
        Main function to track when LMC/UMC introduce words that get picked up
        """
        results = []
        
        for idx, row in self.data.iterrows():
            novel_words = self.detect_novel_words(row['paratext'])
            
            # If this is an LMC/UMC speaker introducing novel words
            if row['dynamic_income'] in inc_cat and novel_words:
                
                # Look ahead to see if these words get picked up
                # Within next N number of paragraphs, defined by the "lookback window"
                future_data = self.data[self.data.index > idx].head(lookback_window)
                
                for word in novel_words:
                    adoption_info = self.measure_word_adoption(
                        word, future_data, row['dynamic_income']
                    )
                    
                    if adoption_info['adopted']:
                        results.append({
                            'introducing_paragraph_id': row['pid'],
                            'introducing_speaker': row['dynamic_income'],
                            'year': row['year'],
                            'meetingno': row['meetingno'],
                            'position': row['paranum'],
                            'novel_word': word,
                            **adoption_info ## dictionary unpacking command; takes pairs and inserts
                        })
        
        return pd.DataFrame(results)
    
    def measure_word_adoption(self, word, future_data, introducing_category):
        """Measure if and how a word gets adopted by other speakers"""
        adopting_speakers = []
        adoption_positions = []
        
        for _, future_row in future_data.iterrows():
            if word in future_row['paratext'].lower():
                if future_row['dynamic_income'] != introducing_category:
                    adopting_speakers.append(future_row['dynamic_income'])
                    adoption_positions.append(future_row['paranum'])
        
        return {
            'adopted': len(adopting_speakers) > 0,
            'num_adopters': len(adopting_speakers),
            'adopting_categories': list(set(adopting_speakers)),
            'first_adoption_position': min(adoption_positions) if adoption_positions else None,
            'adoption_lag': min(adoption_positions) - future_data.iloc[0]['paranum'] if adoption_positions else None
        }
    
## Change point analysis:

class DiscussionPatternDetector:
    def __init__(self, data):
        self.data = data.sort_values(['year', 'meetingno', 'paranum'])
    
    def detect_vocabulary_shifts(self, window_size=10):
        """Detect points where vocabulary changes significantly"""
        similarities = []
        positions = []
        
        # Create rolling windows of vocabulary
        for i in range(window_size, len(self.data) - window_size):
            before_texts = ' '.join(self.data.iloc[i-window_size:i]['paratext'])
            after_texts = ' '.join(self.data.iloc[i:i+window_size]['paratext'])
            
            # Use TF-IDF to compare vocabulary
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            try:
                vectors = vectorizer.fit_transform([before_texts, after_texts])
                 #vector[0] is before texts, vector[1] is after texts
                similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0] #[0][0]  takes first row, scalar value
                similarities.append(similarity)
                positions.append(self.data.iloc[i]['paranum'])
            except:
                continue
        
        # Find change points (low similarity = big vocabulary shift)
        change_threshold = np.percentile(similarities, 25)  # Bottom quartile
        change_points = []
        
        for i, sim in enumerate(similarities):
            if sim < change_threshold:
                change_points.append({
                    'position': positions[i],
                    'similarity_score': sim,
                    'pid': self.data.iloc[i + window_size]['pid']
                })
        
        return change_points
    
    def find_lmc_umc_before_changes(self, change_points, inc_cat, lookback=5):
        
        ## normalize string or list inputs into a list:
        ## for .isin() call later
        ## also verify that they're in the list of income categories:
        if isinstance(inc_cat, str):
            inc_cat = [inc_cat]
    
        income_cats = ['Nonstate', 'Lower middle income', 'High income',
                   'Upper middle income', 'Low income', 'Aggregated']
    
        if not all(cat in income_cats for cat in inc_cat):
            print(f'Income category must match one of {income_cats}!')
            return

        """Check if LMC/UMC speakers appear before vocabulary change points"""
        leadership_moments = [] 
        
        for cp in change_points:
            # Look at paragraphs before the change point
            before_change = self.data[
                (self.data['paranum'] >= cp['position'] - lookback) &
                (self.data['paranum'] < cp['position'])
            ]
            
            cat_speakers = before_change[
                before_change['dynamic_income'].isin(inc_cat) #inc_cat assumed as list:
            ]
            
            if not cat_speakers.empty:
                leadership_moments.append({
                    'change_point_position': cp['position'],
                    'change_similarity': cp['similarity_score'],
                    'cat_speakers_before': len(cat_speakers),
                    'last_lmc_umc_speaker': cat_speakers.iloc[-1]['dynamic_income'],
                    'last_lmc_umc_position': cat_speakers.iloc[-1]['paranum'],
                    'lag_to_change': cp['position'] - cat_speakers.iloc[-1]['paranum']
                })
        
        return pd.DataFrame(leadership_moments)

# Usage example:
def analyze_leadership_through_change_points(data, inc_cat):
    """Main analysis function"""
    
    # 1. Detect vocabulary diffusion
    vocab_detector = VocabularyDiffusionDetector(data)
    diffusion_results = vocab_detector.track_vocabulary_diffusion(inc_cat=inc_cat)
    
    print(f"Found {len(diffusion_results)} instances of identified income categories introducing words that got adopted")
    print("\nTop vocabulary innovations:")
    #print(diffusion_results.columns.tolist()) # list is empty...
    print(diffusion_results.nlargest(10, 'num_adopters')[['year', 'novel_word', 'num_adopters', 'adopting_categories']])
    
    # 2. Detect discussion pattern changes
    pattern_detector = DiscussionPatternDetector(data)
    change_points = pattern_detector.detect_vocabulary_shifts()
    
    print(f"\nFound {len(change_points)} vocabulary change points")
    
    # 3. Link LMC/UMC interventions to changes
    leadership_moments = pattern_detector.find_lmc_umc_before_changes(change_points, 
                                                                      inc_cat)
    
    print(f"\nFound {len(leadership_moments)} potential leadership moments where {inc_cat} speakers preceded vocabulary shifts")
    
    return {
        'vocabulary_diffusion': diffusion_results,
        'change_points': change_points,
        'leadership_moments': leadership_moments
    }

# Run the analysis
# results = analyze_leadership_through_change_points(your_data, inc_cat)