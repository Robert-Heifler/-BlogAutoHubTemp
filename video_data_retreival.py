import os
import csv
import random
from youtube_transcript_api import YouTubeTranscriptApi

# -------------------------------
# CONFIGURATION
# -------------------------------
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Render secret

OUTPUT_FILE = "Final_Full_QA_With_Transcripts.txt"

# -------------------------------
# FULL VIDEO LIST
# -------------------------------
videos = [
    ("_rSW3GikiKs", "7 Minutes Daily"),
    ("_rSW3GikiKs", "Click Wealth System"),
    ("13z9A5kuKkI", "Breathe"),
    ("3rP1xV1rj44", "GlucoTrust"),
    ("5ItORcHZ7RE", "AI Marketers Club by John Crestani"),
    ("7XH6F6kL4l8", "GlucoTrust"),
    ("95hX_OMuIpg", "7 Minutes Daily"),
    ("95hX_OMuIpg", "Click Wealth System"),
    ("9aHLmLaYQm8", "Back to Life"),
    ("bXKQhBK3Z4k", "All Day Slimming Tea"),
    ("GfN_n6j07Fc", "2025 Recession Profit Secrets V3"),
    ("HuAj2MvYS-g", "Alpilean"),
    ("LC3Zu4puC1w", "Back to Life"),
    ("lqf1xtQ2zNo", "BioVanish"),
    ("M-OcJpEfqV0", "BioVanish"),
    ("NuULKH5pJDI", "Fast Wealth"),
    ("O_DafUjazg0", "All Day Slimming Tea"),
    ("TB54dZkzZOY", "Back to Life"),
    ("uQOa5g9nPaw", "Back to Life"),
    ("w8UY4uiVpmQ", "Alpilean"),
    ("XhkfrTkqaLA", "AI Marketers Club by John Crestani"),
    ("Xn6K2tONHhk", "Fast Wealth"),
    ("Xn6K2tONHhk", "FREE Traffic System"),
    ("Xn6K2tONHhk", "Get Paid to be a Virtual Online Assistant - Remote Work Jobs"),
    ("Xn6K2tONHhk", "Get Paid To Use Facebook, Twitter and YouTube"),
    ("XqTjSeAavjE", "2025 Recession Profit Secrets V3"),
    ("y5w6xIoNDhM", "Female Vitality Protocol"),
    ("y5w6xIoNDhM", "Flat Belly Fix"),
    ("yCmsZUN4r_s", "Breathe"),
    ("zWaVz9m3S_k", "Breathe"),
    ("ZX_C58IUss8", "BioVanish")
]

# -------------------------------
# PRODUCT TYPE MAPPING
# -------------------------------
product_types = {
    "7 Minutes Daily": "fitness",
    "Click Wealth System": "course",
    "Breathe": "media",
    "GlucoTrust": "supplement",
    "AI Marketers Club by John Crestani": "course",
    "All Day Slimming Tea": "supplement",
    "2025 Recession Profit Secrets V3": "course",
    "Alpilean": "supplement",
    "Back to Life": "media",
    "BioVanish": "supplement",
    "Fast Wealth": "course",
    "FREE Traffic System": "course",
    "Get Paid to be a Virtual Online Assistant - Remote Work Jobs": "course",
    "Get Paid To Use Facebook, Twitter and YouTube": "course",
    "Female Vitality Protocol": "supplement",
    "Flat Belly Fix": "supplement"
}

# -------------------------------
# QUESTION AND ANSWER TEMPLATES PER TYPE
# Expanded for 20+ templates each type
# -------------------------------
qa_templates = {
    "supplement": [
        ("Does {product} really work?", "Yes, {product} uses scientifically-backed ingredients to deliver results."),
        ("What are the benefits of {product}?", "{product} supports weight management, energy, and overall wellness."),
        ("Is {product} safe?", "Yes, {product} is made with natural ingredients and is safe when used as directed."),
        ("How soon will I see results with {product}?", "Most users notice changes within a few weeks of consistent use."),
        ("Can {product} be combined with other supplements?", "Yes, it can safely complement other wellness products."),
        ("Where can I buy {product}?", "You can purchase {product} from official online stores or verified sellers."),
        ("Is {product} suitable for all ages?", "Yes, most adults can safely use {product} as recommended."),
        ("Does {product} have side effects?", "No serious side effects reported when used properly."),
        ("Can I take {product} with food?", "Yes, taking with food may help absorption."),
        ("How does {product} compare to other supplements?", "{product} has unique ingredients that enhance results."),
        ("Does {product} help with energy levels?", "Yes, users report improved energy and alertness."),
        ("Is {product} clinically tested?", "Many ingredients in {product} are supported by clinical research."),
        ("Can {product} support weight loss naturally?", "Yes, it helps metabolism and fat-burning naturally."),
        ("What is the recommended dosage of {product}?", "Follow the instructions on the official product label."),
        ("Does {product} support immune health?", "Yes, several ingredients in {product} boost immunity."),
        ("Is {product} vegan-friendly?", "Check individual product details, many are plant-based."),
        ("Can {product} help with digestion?", "Some ingredients promote healthy gut function."),
        ("Does {product} have customer reviews?", "Yes, positive reviews are widely available online."),
        ("Can {product} be taken long-term?", "Yes, long-term use is generally considered safe."),
        ("Is {product} suitable for people with allergies?", "Check the ingredient list; most are allergy-friendly."),
        ("How effective is {product} for metabolism?", "It contains ingredients that boost metabolic function naturally."),
        ("Does {product} improve overall wellness?", "Yes, users report better health, energy, and mood after regular use.")
    ],
    "course": [
        ("What will I learn from {product}?", "{product} provides step-by-step guidance to master the topic."),
        ("Is {product} beginner friendly?", "Yes, {product} is structured for all experience levels."),
        ("How long does it take to complete {product}?", "Completion time varies but most finish within weeks."),
        ("Does {product} offer practical exercises?", "Yes, {product} includes hands-on exercises and examples."),
        ("Are there testimonials for {product}?", "Yes, many students share their success stories."),
        ("Can I access {product} online?", "Yes, {product} is fully available online after enrollment."),
        ("Does {product} provide certification?", "Some courses provide a certificate upon completion."),
        ("Are course materials downloadable?", "Yes, all resources are accessible online and downloadable."),
        ("Is {product} suitable for professionals?", "Yes, it covers beginner to advanced levels."),
        ("How is the course structured?", "Step-by-step modules with videos, PDFs, and exercises."),
        ("Can I join from any country?", "Yes, online access is global."),
        ("Does {product} include support?", "Yes, student support is available via email or chat."),
        ("What skills will I gain from {product}?", "You’ll gain practical skills to implement immediately."),
        ("Are there any hidden costs?", "No, the full course price is upfront and clear."),
        ("Is {product} updated regularly?", "Yes, content is kept current with industry standards."),
        ("Does {product} provide templates?", "Many courses include templates, check details."),
        ("How do I start {product}?", "Sign up online and follow the first module instructions."),
        ("Can I pause and resume the course?", "Yes, you can learn at your own pace."),
        ("Is there a money-back guarantee?", "Some courses offer a satisfaction guarantee."),
        ("Are there advanced modules?", "Yes, advanced topics are included for experienced users."),
        ("Does {product} teach real-world applications?", "Yes, practical real-world exercises are included.")
    ],
    "fitness": [
        ("Can {product} help me lose belly fat?", "Yes, {product} combines HIIT and core workouts for effective results."),
        ("Is {product} suitable for beginners?", "Yes, exercises can be modified for all fitness levels."),
        ("How many days per week should I do {product}?", "5–6 days a week is recommended for best outcomes."),
        ("Does {product} improve cardiovascular health?", "Yes, high-intensity intervals boost heart health."),
        ("Do I need extra equipment for {product}?", "No, most routines require only bodyweight exercises."),
        ("Can I combine {product} with other workouts?", "Yes, it complements strength training and yoga routines."),
        ("Will {product} tone muscles effectively?", "Yes, consistent practice builds muscle tone and endurance."),
        ("How long is each session of {product}?", "Each session is designed to be short, typically 7–15 minutes."),
        ("Can I do {product} at home?", "Yes, no gym required; perfect for home workouts."),
        ("Does {product} include warm-up and cool-down?", "Yes, brief warm-up and stretching routines are included."),
        ("Can {product} help improve flexibility?", "Yes, exercises also promote better mobility."),
        ("Is {product} safe for seniors?", "Low-impact modifications make it safe for older adults."),
        ("Does {product} increase energy?", "Users report higher energy levels after regular sessions."),
        ("Can {product} reduce stress?", "Exercise promotes mental clarity and reduces stress."),
        ("Is {product} suitable for weight loss?", "Yes, it combines cardio and strength for effective fat loss."),
        ("Does {product} help posture?", "Yes, core-focused routines improve posture over time."),
        ("Can I do {product} without a coach?", "Yes, instructions are simple and self-guided."),
        ("How do I track progress with {product}?", "Use body measurements and performance logs."),
        ("Is {product} quick to fit into my schedule?", "Yes, each session is just minutes long."),
        ("Does {product} offer variations?", "Yes, alternative moves are provided for variety."),
        ("Can {product} complement yoga or pilates?", "Yes, it integrates well with other fitness routines.")
    ],
    "media": [
        ("Can I use {product} for relaxation?", "Yes, {product} helps reduce stress and promote mental clarity."),
        ("Is {product} good for focus?", "Yes, listeners often experience improved concentration."),
        ("Can {product} be used for meditation?", "Absolutely, ideal for meditation or yoga sessions."),
        ("Will {product} improve sleep?", "Listening before bed can enhance sleep quality."),
        ("Does {product} reduce anxiety?", "Yes, calming rhythms help alleviate anxiety."),
        ("Can {product} be used during workouts?", "Yes, suitable for cooldown or light exercise sessions."),
        ("Is {product} suitable for studying?", "Yes, helps maintain concentration and focus."),
        ("Does {product} enhance creativity?", "Yes, music can stimulate creative thinking."),
        ("Can {product} boost mood?", "Yes, calming melodies improve mood and reduce stress."),
        ("Is {product} good for background listening?", "Yes, perfect for work or leisure background music."),
        ("Can {product} help with mindfulness?", "Yes, supports mindfulness and presence in the moment."),
        ("Is {product} beneficial for mental health?", "Listening regularly can reduce tension and anxiety."),
        ("Does {product} help with productivity?", "Yes, helps maintain focus during tasks."),
        ("Can it be used for relaxation before sleep?", "Yes, encourages deep relaxation and calm."),
        ("Is it safe for all ages?", "Yes, suitable for adults and teens."),
        ("Does {product} have online availability?", "Yes, streams are accessible on multiple platforms."),
        ("Is it free or paid?", "Check availability; some tracks are free to listen."),
        ("Can I share with friends?", "Yes, music can be shared legally if licensed."),
        ("Does it support meditation apps?", "Yes, compatible with popular meditation apps."),
        ("Are there variations of {product}?", "Yes, different versions and mixes are available.")
    ]
}

# -------------------------------
# SCRIPT EXECUTION
# -------------------------------
all_rows = []

for video_id, product_name in videos:
    product_type = product_types.get(product_name, "supplement")
    templates = qa_templates[product_type]
    
    # Ensure unique random selection
    selected_templates = random.sample(templates, 6)
    
    # Retrieve transcript if available
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
    except Exception:
        transcript_text = "Transcript not available."
    
    # Generate rows
    for q_template, a_template in selected_templates:
        question = q_template.format(product=product_name)
        answer = a_template.format(product=product_name)
        # For SEO: use unique keywords per video
        keywords = ", ".join([
            product_name, product_type, "review", "buy", "benefits", "top rated", 
            "best price", "official", "testimonials", "results", "how to", "tips", 
            "guide", "experience", "customer feedback", "natural", "safe", "ingredients"
        ])
        all_rows.append([video_id, product_name, question, answer, keywords, transcript_text])

# -------------------------------
# OUTPUT TO TAB-DELIMITED TXT
# -------------------------------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["VideoID", "ProductName", "Question", "Answer", "Keywords", "Transcript"])
    writer.writerows(all_rows)

print(f"Script completed. {len(all_rows)} rows written to {OUTPUT_FILE}")
