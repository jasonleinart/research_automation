# Tag Guidelines for ArXiv Content Automation System

## 🎯 Core Principles

### 1. **Generalization Over Specificity**
- ❌ `attention-is-all-you-need` → ✅ `transformer-architecture`
- ❌ `step-1:-tokenization` → ✅ `tokenization`
- ❌ `theagentcompany` → ✅ `benchmarking`

### 2. **Reusability Across Papers**
- Tags should be applicable to multiple papers
- Avoid paper-specific names, dates, or unique identifiers
- Focus on concepts, methods, and domains that appear in multiple contexts

### 3. **Consistent Naming Convention**
- Use lowercase with hyphens: `machine-learning`, `neural-networks`
- Keep tags concise (2-3 words maximum)
- Avoid special characters except hyphens

## 📋 Tag Categories and Guidelines

### **RESEARCH_DOMAIN** (Broad academic fields)
**Purpose**: High-level categorization of research areas

**Examples**:
- `artificial-intelligence`
- `machine-learning`
- `natural-language-processing`
- `computer-vision`
- `robotics`
- `data-science`
- `human-computer-interaction`
- `cognitive-science`

**Guidelines**:
- Use established academic domain names
- Be broad enough to encompass multiple subfields
- Avoid overly specific or emerging terms

### **CONCEPT** (Key theoretical concepts and ideas)
**Purpose**: Important concepts, theories, and frameworks

**Examples**:
- `transformer-architecture`
- `attention-mechanism`
- `reinforcement-learning`
- `supervised-learning`
- `unsupervised-learning`
- `deep-learning`
- `neural-networks`
- `language-models`
- `agents`
- `benchmarking`

**Guidelines**:
- Extract the core concept, not the specific implementation
- Use standard terminology from the field
- Avoid paper-specific names or versions

### **METHODOLOGY** (Approaches, techniques, and processes)
**Purpose**: Methods, algorithms, and procedural approaches

**Examples**:
- `tokenization`
- `embedding`
- `fine-tuning`
- `transfer-learning`
- `data-integration`
- `persona-targeting`
- `multimodal-processing`
- `retrieval-augmented-generation`
- `collaborative-filtering`
- `statistical-analysis`

**Guidelines**:
- Focus on the method, not the step number
- Use standard methodological terms
- Avoid paper-specific implementation details

### **APPLICATION** (Use cases and practical applications)
**Purpose**: Real-world applications and use cases

**Examples**:
- `advertising`
- `recommendation-systems`
- `chatbots`
- `autonomous-vehicles`
- `healthcare`
- `education`
- `finance`
- `e-commerce`
- `social-media`
- `content-generation`

**Guidelines**:
- Focus on the application domain, not specific companies
- Use broad industry or sector names
- Avoid proprietary or company-specific applications

### **INNOVATION_MARKER** (Type of contribution)
**Purpose**: Categorize the type of research contribution

**Examples**:
- `novel-framework`
- `survey-review`
- `empirical-study`
- `benchmark-comparison`
- `case-study`
- `position-paper`
- `tutorial`
- `reproduction-study`
- `extension-work`

**Guidelines**:
- Reflect the paper's contribution type
- Use standard research contribution categories
- Help identify the paper's role in the literature

## 🚫 What NOT to Tag

### **Paper-Specific Content**
- ❌ Paper titles or names
- ❌ Author names
- ❌ Specific dataset names (unless widely used)
- ❌ Company or organization names
- ❌ Version numbers or dates

### **Overly Granular Details**
- ❌ Step numbers (`step-1`, `step-2`)
- ❌ Specific parameter values
- ❌ Implementation details
- ❌ File formats or technical specifications

### **Temporary or Context-Specific Terms**
- ❌ Trending buzzwords
- ❌ Conference-specific terminology
- ❌ Unproven or experimental concepts
- ❌ Internal project names

## ✅ Tag Quality Checklist

Before creating a new tag, ask:

1. **Will this tag apply to multiple papers?**
   - If only 1 paper, it's too specific

2. **Is this a standard term in the field?**
   - Use established terminology, not paper-specific terms

3. **Is this the right level of abstraction?**
   - Not too broad (useless) or too narrow (paper-specific)

4. **Is the naming consistent?**
   - Lowercase, hyphens, concise

5. **Does it add value for discovery?**
   - Will researchers want to find papers with this tag?

## 🔧 Tag Creation Process

### **Step 1: Extract Core Concepts**
From: "Step 1: Tokenization of input text"
Extract: `tokenization` (not `step-1-tokenization`)

### **Step 2: Generalize Specific Terms**
From: "Attention Is All You Need framework"
Extract: `transformer-architecture` (not `attention-is-all-you-need`)

### **Step 3: Use Standard Terminology**
From: "Retrieval-augmented generation (RAG)"
Extract: `retrieval-augmented-generation` (not `rag`)

### **Step 4: Categorize Appropriately**
- Domain: `natural-language-processing`
- Concept: `transformer-architecture`
- Methodology: `attention-mechanism`
- Application: `language-modeling`

## 📊 Tag Usage Metrics

### **Target Metrics**
- **Reusability**: Each tag should apply to 2+ papers
- **Coverage**: 80%+ of papers should have tags
- **Balance**: No single tag should dominate (>30% of papers)
- **Diversity**: Mix of categories across papers

### **Quality Indicators**
- High-confidence tags (≥80%)
- Consistent application across similar papers
- Useful for filtering and discovery
- Aligns with research community terminology

## 🛠️ Implementation Guidelines

### **Automatic Tag Generation**
1. Extract key terms from insights
2. Apply generalization rules
3. Check against existing tag vocabulary
4. Assign appropriate category
5. Calculate confidence score

### **Manual Tag Review**
1. Review automatically generated tags
2. Merge similar tags
3. Remove paper-specific tags
4. Add missing high-level tags
5. Validate against guidelines

### **Tag Maintenance**
1. Regular review of low-usage tags
2. Merge similar tags
3. Update tag descriptions
4. Monitor tag quality metrics
5. Archive obsolete tags

## 📈 Example Tag Transformations

### **Before (Problematic)**
```
attention-is-all-you-need
step-1:-tokenization
step-2:-embedding
theagentcompany
agentic-multimodal-ai-for-hyperpersonalized-b2b-and-b2c-advertising
```

### **After (Generalized)**
```
transformer-architecture
tokenization
embedding
benchmarking
multimodal-ai
advertising
persona-targeting
```

This approach ensures tags are:
- ✅ Reusable across multiple papers
- ✅ Standard terminology
- ✅ Appropriate abstraction level
- ✅ Useful for discovery and filtering
- ✅ Consistent naming convention 