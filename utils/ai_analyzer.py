import google.generativeai as genai
import json
import re
from config import Config
import streamlit as st

class AIAnalyzer:
    def __init__(self):
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # Updated model name - try multiple options
            self.model_names = [
                'gemini-1.5-flash',  # Current model name
                'gemini-1.5-pro',    # Alternative
                'gemini-pro',        # Fallback
                'models/gemini-1.5-flash',  # With models prefix
                'models/gemini-1.5-pro'     # With models prefix
            ]
            self.model = self._initialize_model()
        except Exception as e:
            print(f"AI Analyzer initialization error: {str(e)}")
            self.model = None
    
    def _initialize_model(self):
        """Try to initialize model with available names"""
        for model_name in self.model_names:
            try:
                model = genai.GenerativeModel(model_name)
                # Test the model with a simple prompt
                response = model.generate_content("Hello")
                if response.text:
                    print(f"Successfully initialized model: {model_name}")
                    return model
            except Exception as e:
                print(f"Failed to initialize {model_name}: {str(e)}")
                continue
        
        print("Warning: No Gemini models available - using fallback analysis")
        return None
    
    def analyze_ticket(self, ticket):
        """Analyze a single ticket with AI"""
        try:
            if not self.model:
                return self._fallback_analysis(ticket)
                
            prompt = self._create_analysis_prompt(ticket)
            response = self.model.generate_content(prompt)
            
            if response.text:
                analysis = self._parse_ai_response(response.text)
                return {
                    'success': True,
                    'ticket_id': ticket['id'],
                    'analysis': analysis
                }
            else:
                return self._fallback_analysis(ticket)
                
        except Exception as e:
            print(f"AI analysis failed for {ticket['id']}: {str(e)}")
            return self._fallback_analysis(ticket)
    
    def analyze_tickets_batch(self, tickets):
        """Analyze multiple tickets"""
        results = []
        
        if not tickets:
            return results
            
        # Show progress bar only if we have tickets
        progress_bar = st.progress(0)
        
        for i, ticket in enumerate(tickets):
            result = self.analyze_ticket(ticket)
            results.append(result)
            progress_bar.progress((i + 1) / len(tickets))
        
        progress_bar.empty()
        return results
    
    def _create_analysis_prompt(self, ticket):
        """Create AI analysis prompt"""
        return f"""Analyze this IT support ticket and provide a JSON response:

TICKET ID: {ticket.get('id', 'Unknown')}
SUMMARY: {ticket.get('summary', 'No summary')}
DESCRIPTION: {ticket.get('description', 'No description')}
CURRENT CATEGORY: {ticket.get('category', 'General')}
PRIORITY: {ticket.get('priority', 'Medium')}

Provide your analysis in this exact JSON format:
{{
  "category": "Hardware|Software|Network|Security|General",
  "priority": "Critical|High|Medium|Low",
  "confidence": 0.85,
  "urgency_score": 7,
  "complexity_score": 5,
  "estimated_resolution_time": "2 hours",
  "suggested_solutions": [
    {{
      "title": "Primary Solution",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "confidence": 0.9,
      "estimated_time": "30 minutes"
    }}
  ],
  "knowledge_base_search": ["keyword1", "keyword2"],
  "escalation_triggers": ["trigger1"],
  "risk_assessment": "Low|Medium|High"
}}

Focus on practical IT solutions. Be specific and actionable."""
    
    def _parse_ai_response(self, response_text):
        """Parse AI response and extract JSON"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                analysis = json.loads(json_str)
                
                # Validate and set defaults
                analysis = {
                    'category': analysis.get('category', 'General'),
                    'priority': analysis.get('priority', 'Medium'),
                    'confidence': float(analysis.get('confidence', 0.5)),
                    'urgency_score': int(analysis.get('urgency_score', 5)),
                    'complexity_score': int(analysis.get('complexity_score', 5)),
                    'estimated_resolution_time': analysis.get('estimated_resolution_time', 'Unknown'),
                    'suggested_solutions': analysis.get('suggested_solutions', []),
                    'knowledge_base_search': analysis.get('knowledge_base_search', []),
                    'escalation_triggers': analysis.get('escalation_triggers', []),
                    'risk_assessment': analysis.get('risk_assessment', 'Medium')
                }
                
                return analysis
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"Failed to parse AI response: {str(e)}")
            return self._create_fallback_analysis()
    
    def _create_fallback_analysis(self):
        """Create fallback analysis when AI fails"""
        return {
            'category': 'General',
            'priority': 'Medium',
            'confidence': 0.3,
            'urgency_score': 5,
            'complexity_score': 5,
            'estimated_resolution_time': 'Manual review required',
            'suggested_solutions': [{
                'title': 'Manual Review Required',
                'steps': ['Review ticket details', 'Analyze requirements', 'Provide custom solution'],
                'confidence': 0.3,
                'estimated_time': 'Variable'
            }],
            'knowledge_base_search': [],
            'escalation_triggers': ['Manual review needed'],
            'risk_assessment': 'Medium'
        }
    
    def _fallback_analysis(self, ticket):
        """Return fallback analysis result"""
        return {
            'success': True,
            'ticket_id': ticket.get('id', 'Unknown'),
            'analysis': self._create_fallback_analysis()
        }