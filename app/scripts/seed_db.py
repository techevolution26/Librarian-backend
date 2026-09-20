from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Book, Notification

BOOK_SEED = [
  {
    "title": "Mere Christianity",
    "author": "C.S. Lewis",
    "cover": "/merechristianity.png",
    "description": "A classic exploration of the common ground upon which all of those of Christian faith stand together.",
    "rating": 4.8,
    "pages": 251,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Purpose Driven Life",
    "author": "Rick Warren",
    "cover": "/thepurposedrivenlife.jpg",
    "description": "A 40-day spiritual journey to help you understand why you are alive and God's amazing plan for you.",
    "rating": 4.7,
    "pages": 340,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Crazy Love",
    "author": "Francis Chan",
    "cover": "/crazylove.jpg",
    "description": "A call for Christians to fall in love with God and live out their faith in a radical way.",
    "rating": 4.7,
    "pages": 224,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Case for Christ",
    "author": "Lee Strobel",
    "cover": "/thecaseforchrist.jpg",
    "description": "A journalist's personal investigation of the evidence for Jesus Christ.",
    "rating": 4.8,
    "pages": 263,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Holy Bible (KJV)",
    "author": "Various Authors",
    "cover": "/kingjamesbibleholybiblekjvannotated.jpg",
    "description": "The King James Version of the Holy Bible.",
    "rating": 5.0,
    "pages": 742,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None

  },
  {
    "title": "Knowing God",
    "author": "J.I. Packer",
    "cover": "/knowinggod.jpg",
    "description": "A profound work that reveals the character and majesty of God.",
    "rating": 4.8,
    "pages": 535,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Pursuit of God",
    "author": "A.W. Tozer",
    "cover": "/thepursuitofgod.png",
    "description": "A thirsty cry for a deeper life with God.",
    "rating": 4.8,
    "pages": 128,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Desiring God",
    "author": "John Piper",
    "cover": "/desiringgod.jpg",
    "description": "Finding supreme joy in God through 'Christian Hedonism.'",
    "rating": 4.7,
    "pages": 399,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Gentle and Lowly",
    "author": "Dane Ortlund",
    "cover": "/gentleandlowly.jpg",
    "description": "An exploration of the heart of Christ for sinners and sufferers.",
    "rating": 4.8,
    "pages": 224,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Radical",
    "author": "David Platt",
    "cover": "/radical-David-Platt.jpg",
    "description": "Taking back your faith from the American Dream.",
    "rating": 4.7,
    "pages": 26,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Holy Bible",
    "author": "Various Authors",
    "cover": "/theholybible.jpg",
    "description": "Translated out of the Original Tongues: and with the Former Translations Diligently Comparedand Revised, by His Majesty’s Special Command.",
    "rating": 5.0,
    "pages": 2462,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Holy Bible (LSV)",
    "author": "Various Authors",
    "cover": "/theholybible-lsv.jpg",
    "description": "The Literal Standard Version of the Holy Bible.",
    "rating": 5.0,
    "pages": 771,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Prayer Fasting & the Pursuit of God",
    "author": "David Platt",
    "cover": "/prayerfastingandthepursuitofgod-david-platt.jpeg",
    "description": "A practical guide to prayer, fasting, and the pursuit of God.",
    "rating": 4.6,
    "pages": 260,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Holy Bible (NIV)",
    "author": "Various Authors",
    "cover": "/theholybible-niv.jpg",
    "description": "The New International Version of the Holy Bible.",
    "rating": 5.0,
    "pages": 1751,
    "genre": ["Christianity", "Faith"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },

  #--- PRODUCTIVITY ---
  {
    "title": "Atomic Habits",
    "author": "James Clear",
    "cover": "/atomichabits.jpg",
    "description": "Tiny changes, remarkable results through habit stacking and identity shift.",
    "rating": 4.8,
    "pages": 320,
    "genre": ["Productivity","Self-Help","Health"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Deep Work",
    "author": "Cal Newport",
    "cover": "/deepwork-calnewport.webp",
    "description": "Rules for focused success in a distracted world.",
    "rating": 4.7,
    "pages": 190,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The 7 Habits of Highly Effective People",
    "author": "Stephen Covey",
    "cover": "/the7habitsofhighlyeffectivepeople-25th-Anni-Edition.png",
    "description": "A principle-centered approach for solving personal and professional problems.",
    "rating": 4.8,
    "pages": 282,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Eat That Frog!",
    "author": "Brian Tracy",
    "cover": "/eatthatfrog-brian-tracy.jpg",
    "description": "21 great ways to stop procrastinating and get more done in less time.",
    "rating": 4.7,
    "pages": 127,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Essentialism",
    "author": "Greg McKeown",
    "cover": "/essentialism.jpg",
    "description": "The disciplined pursuit of less.",
    "rating": 4.6,
    "pages": 236,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Power of Habit",
    "author": "Charles Duhigg",
    "cover": "/thepowerofhabit-in-life-business.jpg",
    "description": "Why we do what we do in life and business.",
    "rating": 4.6,
    "pages": 422,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Getting Things Done",
    "author": "David Allen",
    "cover": "/gettingthingsdone.jpeg",
    "description": "The art of stress-free productivity.",
    "rating": 4.5,
    "pages": 402,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Indistractable",
    "author": "Nir Eyal",
    "cover": "/indistractable-how-tocontrol-your-attentio.webp",
    "description": "How to control your attention and choose your life.",
    "rating": 4.6,
    "pages": 265,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Make Time",
    "author": "Jake Knapp",
    "cover": "/maketime.jpg",
    "description": "How to focus on what matters every day.",
    "rating": 4.5,
    "pages": 277,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The 5 AM Club",
    "author": "Robin Sharma",
    "cover": "/the5amclub.jpeg",
    "description": "Own your morning. Elevate your life.",
    "rating": 4.4,
    "pages": 252,
    "genre": ["Productivity"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },

  # --- MINDSET & SELF-HELP ---
  {
    "title": "Man's Search for Meaning",
    "author": "Viktor Frankl",
    "cover": "/manssearchformeaning.jpg",
    "description": "A psychiatrist's memoir of life in Nazi death camps and its lessons for spiritual survival.",
    "rating": 4.9,
    "pages": 148,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Can't Hurt Me",
    "author": "David Goggins",
    "cover": "/canthurtme.jpg",
    "description": "Master your mind and defy the odds.",
    "rating": 4.8,
    "pages": 306,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Daring Greatly",
    "author": "Brene Brown",
    "cover": "/daringgreatly.jpg",
    "description": "How the courage to be vulnerable transforms the way we live, love, parent, and lead.",
    "rating": 4.7,
    "pages": 304,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Mountain Is You",
    "author": "Brianna Wiest",
    "cover": "/themountainisyou.jpg",
    "description": "Transforming self-sabotage into self-mastery.",
    "rating": 4.7,
    "pages": 248,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "12 Rules for Life",
    "author": "Jordan Peterson",
    "cover": "/12rulesforlife.jpg",
    "description": "An antidote to chaos based on psychological and philosophical insights.",
    "rating": 4.7,
    "pages": 263,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Obstacle Is the Way",
    "author": "Ryan Holiday",
    "cover": "/theobstacleistheway.jpg",
    "description": "The timeless art of turning trials into triumph through Stoic philosophy.",
    "rating": 4.7,
    "pages": 173
    ,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Four Agreements",
    "author": "Don Miguel Ruiz",
    "cover": "/thefouragreements.jpg",
    "description": "A practical guide to personal freedom based on ancient Toltec wisdom.",
    "rating": 4.7,
    "pages": 160,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Mindset: The New Psychology of Success",
    "author": "Carol S. Dweck",
    "cover": "/mindset.jpg",
    "description": "How we can learn to fulfill our potential based on growth vs. fixed mindset.",
    "rating": 4.6,
    "pages": 306,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Thinking, Fast and Slow",
    "author": "Daniel Kahneman",
    "cover": "/thinkingfastandslow.webp",
    "description": "An exploration of the two systems that drive the way we think.",
    "rating": 4.6,
    "pages": 533,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Subtle Art of Not Giving a F*ck",
    "author": "Mark Manson",
    "cover": "/the_subtle_art_of_not_giving_a_fuck.jpg",
    "description": "A counterintuitive approach to living a good life.",
    "rating": 4.4,
    "pages": 152,
    "genre": ["Mindset"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },

  # --- BUSINESS & LEADERSHIP ---
  {
    "title": "Shoe Dog",
    "author": "Phil Knight",
    "cover": "/shoedog.jpg",
    "description": "A memoir by the creator of Nike.",
    "rating": 4.8,
    "pages": 400,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Extreme Ownership",
    "author": "Jocko Willink",
    "cover": "/extremeownership.jpg",
    "description": "How U.S. Navy SEALs lead and win.",
    "rating": 4.8,
    "pages": 209,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Never Split the Difference",
    "author": "Chris Voss",
    "cover": "/neversplitthedifference.jpg",
    "description": "Negotiating as if your life depended on it.",
    "rating": 4.8,
    "pages": 288,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Good to Great",
    "author": "Jim Collins",
    "cover": "/goodtogreat.png",
    "description": "Why some companies make the leap and others don't.",
    "rating": 4.7,
    "pages": 320,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Start with Why",
    "author": "Simon Sinek",
    "cover": "/startwithwhy.jpg",
    "description": "How great leaders inspire everyone to take action.",
    "rating": 4.7,
    "pages": 271,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Hard Thing About Hard Things",
    "author": "Ben Horowitz",
    "cover": "/thehardthing.jpg",
    "description": "Building a business when there are no easy answers.",
    "rating": 4.7,
    "pages": 253,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Leaders Eat Last",
    "author": "Simon Sinek",
    "cover": "/leaderseatlast.jpg",
    "description": "Why some teams pull together and others don't.",
    "rating": 4.7,
    "pages": 296,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Zero to One",
    "author": "Peter Thiel",
    "cover": "/zerotoone.jpg",
    "description": "Notes on startups, or how to build the future.",
    "rating": 4.6,
    "pages": 213,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Lean Startup",
    "author": "Eric Ries",
    "cover": "/theleanstartup.jpg",
    "description": "How constant innovation creates radically successful businesses.",
    "rating": 4.6,
    "pages": 296,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Built to Last",
    "author": "Jim Collins",
    "cover": "/builttolast.jpg",
    "description": "Successful habits of visionary companies.",
    "rating": 4.6,
    "pages": 725,
    "genre": ["Business"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },

  # --- FINANCE ---
  {
    "title": "The Psychology of Money",
    "author": "Morgan Housel",
    "cover": "/psychologyofmoney.jpg",
    "description": "Timeless lessons on wealth, greed, and happiness.",
    "rating": 4.7,
    "pages": 242,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "I Will Teach You to Be Rich",
    "author": "Ramit Sethi",
    "cover": "/iwillteachyou.jpg",
    "description": "A 6-week program that works on your rich life.",
    "rating": 4.7,
    "pages": 448,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Think and Grow Rich",
    "author": "Napoleon Hill",
    "cover": "/thinkandgrowrich.png",
    "description": "The landmark bestseller on personal success.",
    "rating": 4.7,
    "pages": 253,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Richest Man in Babylon",
    "author": "George S. Clason",
    "cover": "/richestmaninbabylon.avif",
    "description": "Success secrets of the ancients.",
    "rating": 4.7,
    "pages": 163,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Rich Dad Poor Dad",
    "author": "Robert Kiyosaki",
    "cover": "/richdadpoordad.jpg",
    "description": "What the rich teach their kids about money that the poor and middle class do not!",
    "rating": 4.6,
    "pages": 241,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Intelligent Investor",
    "author": "Benjamin Graham",
    "cover": "/intelligentinvestor.webp",
    "description": "The definitive book on value investing.",
    "rating": 4.6,
    "pages": 641,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Your Money or Your Life",
    "author": "Vicki Robin",
    "cover": "/yourmoneyoryourlife.jpg",
    "description": "9 steps to transforming your relationship with money and achieving financial independence.",
    "rating": 4.6,
    "pages": 349,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Millionaire Next Door",
    "author": "Thomas J. Stanley",
    "cover": "/millionairenextdoor.jpg",
    "description": "The surprising secrets of America's wealthy.",
    "rating": 4.6,
    "pages": 282,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Die With Zero",
    "author": "Bill Perkins",
    "cover": "/diewithzero.jpg",
    "description": "Getting all you can from your money and your life.",
    "rating": 4.5,
    "pages": 163,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Total Money Makeover",
    "author": "Dave Ramsey",
    "cover": "/thetotalmoneymakeover.jpg",
    "description": "A proven plan for financial fitness.",
    "rating": 4.5,
    "pages": 320,
    "genre": ["Finance"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None

  },

  # --- PSYCHOLOGY & HUMAN BEHAVIOR ---
  {
    "title": "The Body Keeps the Score",
    "author": "Bessel van der Kolk",
    "cover": "/bodykeepsthescore.jpg",
    "description": "Brain, mind, and body in the healing of trauma.",
    "rating": 4.8,
    "pages": 464,
    "genre": ["Psychology","Health"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Influence: The Psychology of Persuasion",
    "author": "Robert Cialdini",
    "cover": "/influence.jpg",
    "description": "The psychology of why people say 'yes.'",
    "rating": 4.7,
    "pages": 297,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Quiet",
    "author": "Susan Cain",
    "cover": "/quiet.jpeg",
    "description": "The power of introverts in a world that can't stop talking.",
    "rating": 4.6,
    "pages": 368,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Predictably Irrational",
    "author": "Dan Ariely",
    "cover": "/predictablyirrational.jpg",
    "description": "The hidden forces that shape our decisions.",
    "rating": 4.6,
    "pages": 304,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Grit",
    "author": "Angela Duckworth",
    "cover": "/grit.jpg",
    "description": "The power of passion and perseverance.",
    "rating": 4.6,
    "pages": 352,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Flow",
    "author": "Mihaly Csikszentmihalyi",
    "cover": "/flow.webp",
    "description": "The psychology of optimal experience.",
    "rating": 4.6,
    "pages": 314,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Emotional Intelligence",
    "author": "Daniel Goleman",
    "cover": "/emotionalintelligence.jpg",
    "description": "Why it can matter more than IQ.",
    "rating": 4.5,
    "pages": 249,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Blink",
    "author": "Malcolm Gladwell",
    "cover": "/blink.jpg",
    "description": "The power of thinking without thinking.",
    "rating": 4.5,
    "pages": 320,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "The Tipping Point",
    "author": "Malcolm Gladwell",
    "cover": "/thetipping Point.jpg",
    "description": "How little things can make a big difference.",
    "rating": 4.5,
    "pages": 287,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
  },
  {
    "title": "Everything is F*cked",
    "author": "Mark Manson",
    "cover": "/everythingisfcked.jpg",
    "description": "A book about hope in a world of despair.",
    "rating": 4.4,
    "pages": 288,
    "genre": ["Psychology"],
    "source_type": "pdf",
    "content_text": "Sample content...",
    "mime_type": "application/pdf",
    "source_url": None,
    "source_path": None
    },
  # ----------technology
    {
      "title": "The Innovators",
      "author": "Walter Isaacson",
      "cover": "/theinnovators.webp",
      "description": "How a group of hackers, geniuses, and geeks created the digital revolution.",
      "rating": 4.7,
      "pages": 560,
      "genre": ["Technology"],
      "source_type": "pdf",
      "content_text": "Sample content...",
      "mime_type": "application/pdf",
      "source_url": None,
      "source_path": None
    },
    {
      "title": "Clean Code",
      "author": "Robert C. Martin",
      "cover": "/cleancode.jpg",
      "description": "A handbook of agile software craftsmanship.",
      "rating": 4.7,
      "pages": 462,
      "genre": ["Technology"],
      "source_type": "pdf",
      "content_text": "Sample content...",
      "mime_type": "application/pdf",
      "source_url": None,
      "source_path": None
    },
    {
        "title": "The Coming Wave",
        "author": "Mustafa Suleyman",
        "cover": "/thecomingwave.webp",
        "description": "A guide to navigating the era of AI and synthetic biology.",
        "rating": 4.4,
        "pages": 432,
        "genre": ["Technology", "Politics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Chip War",
        "author": "Chris Miller",
        "cover": "/chipwar.jpg",
        "description": "The epic battle over the world's most critical technology.",
        "rating": 4.5,
        "pages": 464,
        "genre": ["Technology", "History"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "The Age of Surveillance Capitalism",
        "author": "Shoshana Zuboff",
        "cover": "/surveillancecapitalism.jpg",
        "description": "The fight for a human future at the new frontier of power.",
        "rating": 4.3,
        "pages": 478,
        "genre": ["Technology", "Sociology"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Life 3.0",
        "author": "Max Tegmark",
        "cover": "/life30.jpg",
        "description": "Being human in the age of Artificial Intelligence.",
        "rating": 4.1,
        "pages": 440,
        "genre": ["Technology", "Science"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      # Science
      {
        "title": "Sapiens",
        "author": "Yuval Noah Harari",
        "cover": "/sapiens.jpg",
        "description": "A brief history of humankind from evolution to the future.",
        "rating": 4.4,
        "pages": 439,
        "genre": ["Science", "History"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Astrophysics for People in a Hurry",
        "author": "Neil deGrasse Tyson",
        "cover": "/astrophysics.jpg",
        "description": "Essential universe concepts explained simply.",
        "rating": 4.3,
        "pages": 124,
        "genre": ["Science", "Physics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "The Selfish Gene",
        "author": "Richard Dawkins",
        "cover": "/selfishgene.jpg",
        "description": "A classic look at the biology of selfishness and altruism.",
        "rating": 4.2,
        "pages": 384,
        "genre": ["Science", "Biology"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "The Gene: An Intimate History",
        "author": "Siddhartha Mukherjee",
        "cover": "/thegene.jpg",
        "description": "The story of the quest to decipher the master-code of humanity.",
        "rating": 4.3,
        "pages": 608,
        "genre": ["Science", "Biology"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "An Immense World",
        "author": "Ed Yong",
        "cover": "/immenseworld.jpg",
        "description": "How animal senses reveal the hidden realms around us.",
        "rating": 4.5,
        "pages": 464,
        "genre": ["Science", "Nature"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      # Health
      {
        "title": "Outlive",
        "author": "Peter Attia",
        "cover": "/outlive.jpg",
        "description": "The science and art of longevity and healthspan.",
        "rating": 4.7,
        "pages": 496,
        "genre": ["Health", "Longevity"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Glucose Revolution",
        "author": "Jessie Inchauspé",
        "cover": "/glucoserevolution.jpg",
        "description": "How balancing your blood sugar can transform your life.",
        "rating": 4.6,
        "pages": 320,
        "genre": ["Health", "Nutrition"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Breath",
        "author": "James Nestor",
        "cover": "/breath.jpg",
        "description": "The new science of a lost art and how we breathe.",
        "rating": 4.5,
        "pages": 226,
        "genre": ["Health", "Science"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Why We Sleep",
        "author": "Matthew Walker",
        "cover": "/whywesleep.jpg",
        "description": "Unlocking the power of sleep and dreams.",
        "rating": 4.6,
        "pages": 368,
        "genre": ["Health", "Science"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },

      # university catalogues
      {
        "title": "Shaping The College Curriculum: Academic Plans 2nd Edition",
        "author": "Lisa R. Lattuca and Joan S. Stark",
        "cover": "/shapingcollegecurriculum2nd.jpg",
        "description": "A sample: A collection of academic plans from the University of Chicago between 1892 and 1945, showcasing the evolution of higher education curriculum design.",
        "rating": 4.5,
        "pages": 30,
        "genre": ["Education", "History"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "University Teaching in Focus",
        "author": "Edited by Lynne Hunt and Denise Chalmers",
        "cover": "/universityteachingfocus.jpg",
        "description": "A sample: The second edition of University Teaching in Focus distils the knowledge and insights,of internationally acclaimed experts in university teaching. It empowers university teachers and contributes to their career success by developing their teaching skills, strategies and knowledge..",
        "rating": 4.3,
        "pages": 38,
        "genre": ["Education", "Pedagogy"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "General Education Essentials: A Guide for College Faculty",
        "author": "Paul Hanstedt",
        "cover": "/generaleducationessentials.jpg",
        "description": "A sample: A comprehensive guide to general education principles and practices for college faculty.",
        "rating": 4.2,
        "pages": 28,
        "genre": ["Education", "Pedagogy"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Business Accounting",
        "author": "Joe Ben Hoyle, University of Richmond,C. J. Skender, University of North Carolina at Chapel Hill",
        "cover": "/businessaccounting.webp",
        "description": "A sample: A comprehensive guide to business accounting principles and practices.",
        "rating": 4.3,
        "pages": 1108,
        "genre": ["Business", "Accounting"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Marketing Management",
        "author": "Maharshi Dayanand University",
        "cover": "/marketingmanagement.jpg",
        "description": "A sample: A comprehensive guide to marketing management principles and practices.",
        "rating": 4.4,
        "pages": 487,
        "genre": ["Business", "Marketing"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Marketcing Management 14",
        "author": "Philip Kotler, Northwestern University, Kevin Lane Keller, Dartmouth College",
        "cover": "/marketingmanagement14.jpg",
        "description": "A comprehensive guide to marketing management principles and practices.",
        "rating": 4.5,
        "pages": 812,
        "genre": ["Business", "Marketing"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Principles of Management",
        "author": "Rice University",
        "cover": "/principlesofmanagement.webp",
        "description": "A comprehensive guide to principles of management for business students.",
        "rating": 4.3,
        "pages": 673,
        "genre": ["Business", "Management"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Economics",
        "author": "Unknown",
        "cover": "/economics.jpg",
        "description": "A comprehensive guide to economics principles and practices.",
        "rating": 4.2,
        "pages": 110,
        "genre": ["Business", "Economics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Essential of Business Law 10th edition",
        "author": "Anthony L. Liuzzo, J.D., Ph.D.Wilkes University Mesa, Arizona, Ruth C. Hughes, J.D. ,Wilkes University Wilkes-Barre, Pennsylvania",
        "cover": "/essentialofbusinesslaw10thedition.jpeg",
        "description": "A comprehensive guide to business law principles and practices,.",
        "rating": 4.3,
        "pages": 824,
        "genre": ["Business", "Law"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Chemistry: The Central Science 12th edition",
        "author": "Theodore L. Brown University, Eugene LEMay, RenoBruce E. Bursten, KnoxvilleCatherine J. Murphy,Patrick M. Woodward",
        "cover": "/chemistryscience12thed.webp",
        "description": "A comprehensive guide to chemistry principles and practices,Theodore L. Brown University of Illinois at Urbana-ChampaignH. Eugene LEMay, Jr. University of Nevada, RenoBruce E. Bursten University of Tennessee, KnoxvilleCatherine J. Murphy ,University of Illinois at Urbana-Champaign,Patrick M. Woodward The Ohio State University.",
        "rating": 4.4,
        "pages": 1195,
        "genre": ["Science", "Chemistry"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "University Physics Volume 1",
        "author": "Samuel J. Ling, University of Oregon, Jeff Sanny, University of Oregon, William Moebs, University of Oregon",
        "cover": "/universityphysics.jpg",
        "description": "A comprehensive guide to university physics principles and practices.",
        "rating": 4.5,
        "pages": 998,
        "genre": ["Science", "Physics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Biology",
        "author": "Raven Johnson",
        "cover": "/Biology-6th-ed-raven-johnson-1-320.webp",
        "description": "A comprehensive guide to biology principles and practices.",
        "rating": 4.4,
        "pages": 1239,
        "genre": ["Science", "Biology"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Higher Engineering Mathematics 6th edition",
        "author": "John Bird, B.S. Grewal",
        "cover": "/higherengineeringmathematics.jpg",
        "description": "A comprehensive guide to higher engineering mathematics principles and practices.",
        "rating": 4.3,
        "pages": 705,
        "genre": ["Engineering", "Mathematics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "A Textbook of Electrical Technology Volume 1",
        "author": "B.L. Theraja, A.K. Theraja",
        "cover": "/electricaltechnology.png",
        "description": "A comprehensive guide to electrical technology principles and practices.",
        "rating": 4.2,
        "pages": 2744,
        "genre": ["Engineering", "Electrical"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Engineering Mechanics: Statics",
        "author": "R.C. Hibbeler",
        "cover": "/engineeringmechanicsstatic.jpg",
        "description": "A comprehensive guide to engineering mechanics principles and practices.",
        "rating": 4.3,
        "pages": 655,
        "genre": ["Engineering", "Mechanics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title":"Newnes Workshop Engineers pocket book",
        "author": "Roger Timings",
        "cover": "/newnesworkshopengineerspocketbook.jpg",
        "description": "A comprehensive guide to workshop engineering principles and practices.",
        "rating": 4.1,
        "pages": 315,
        "genre": ["Engineering", "Workshop"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Fluid Mechanics 4th edition",
        "author": "Frank M. White, University of Rhode Island",
        "cover": "/fluidmechanics.jpg",
        "description": "A comprehensive guide to fluid mechanics principles and practices.",
        "rating": 4.2,
        "pages": 1023,
        "genre": ["Engineering", "Fluid Mechanics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Doing Qualitative Research 5th edition",
        "author": "David Silverman",
        "cover": "/doingqualitativeresearch.jpg",
        "description": "A comprehensive guide to qualitative research principles and practices.",
        "rating": 4.3,
        "pages": 931,
        "genre": ["Research", "Qualitative"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Everythings an Argument with Readings:Instructors Notes 4th edition",
        "author": "Andrea Lunsford, Robert E. Scott",
        "cover": "/everythingsanargument.jpg",
        "description": "A comprehensive guide to argumentation principles and practices.",
        "rating": 4.2,
        "pages": 251,
        "genre": ["Communication", "Argumentation"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "The Penguin Dictionary OF International Relations",
        "author": "Graham Evans and Jeffrey Neumham",
        "cover": "/penguindictionaryofinternationalrelations.jpg",
        "description": "A comprehensive guide to international relations principles and practices.",
        "rating": 4.1,
        "pages": 644,
        "genre": ["Politics", "International Relations"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Socialogy 5th edition",
        "author": "Anthony Giddens, Mitchell Duneier, Richard P. Appelbaum, Deborah Carr",
        "cover": "/sociology.jpg",
        "description": "A comprehensive guide to sociology principles and practices.",
        "rating": 4.2,
        "pages": 1121,
        "genre": ["Sociology"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Operating System Concepts 8th edition",
        "author": "Abraham Silberschatz, Peter B. Galvin, Greg Gagne",
        "cover": "/operatingsystemconcepts.jpg",
        "description": "A comprehensive guide to operating system concepts and practices.",
        "rating": 4.4,
        "pages": 976,
        "genre": ["Technology", "Operating Systems"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Operating System Concepts 8th edition",
        "author": "Abraham Silberschatz, Peter B. Galvin, Greg Gagne",
        "cover": "/operatingsystemconcepts.jpg",
        "description": "A comprehensive guide to operating system concepts and practices.",
        "rating": 4.4,
        "pages": 976,
        "genre": ["Technology", "Operating Systems"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Data Communications & Networking 4th Edition",
        "author": "Behrouz A. Forouzan,DeAnza College, Sophia Chung Fegan",
        "cover": "/datacommunicationsandnetworking.jpg",
        "description": "A comprehensive guide to data communications and networking principles and practices.",
        "rating": 4.3,
        "pages": 1171,
        "genre": ["Technology", "Networking"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Data Communications & Networking 5th Edition",
        "author": "Behrouz A. Forouzan,DeAnza College, Sophia Chung Fegan",
        "cover": "/datacommunicationsandnetworking.jpg",
        "description": "A comprehensive guide to data communications and networking principles and practices.",
        "rating": 4.3,
        "pages": 1269,
        "genre": ["Technology", "Networking"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Java How To Program GUI 9th Edition",
        "author": "Paul Deitel, Harvey Deitel",
        "cover": "/javahowtoprogram.jpg",
        "description": "A comprehensive guide to Java programming principles and practices.",
        "rating": 4.4,
        "pages": 1535,
        "genre": ["Technology", "Programming"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Java How To Program GUI 4th Edition",
        "author": "Paul Deitel, Harvey Deitel",
        "cover": "/javahowtoprogram.jpg",
        "description": "A comprehensive guide to Java programming principles and practices.",
        "rating": 4.4,
        "pages": 1530,
        "genre": ["Technology", "Programming"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Java How To Program 10th Edition",
        "author": "Paul Deitel, Harvey Deitel",
        "cover": "/javahowtoprogram10thed.jpg",
        "description": "A comprehensive guide to Java programming principles and practices.",
        "rating": 4.4,
        "pages": 1245,
        "genre": ["Technology", "Programming"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Database System Concepts 7th Edition",
        "author": "Abraham Silberschatz, Henry F. Korth, S. Sudarshan",
        "cover": "/databasesystemconcepts.jpg",
        "description": "A comprehensive guide to database system concepts and practices.",
        "rating": 4.5,
        "pages": 1373,
        "genre": ["Technology", "Databases"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Introduction to Philosophy",
        "author": "Paul J. Glenn",
        "cover": "/introductiontophilosophy.jpg",
        "description": "A comprehensive guide to philosophy principles and practices,Paul J. Glenn ,Ph.D., S.T.D.Professor of Philosophy in the C ollege of St. Charles Borromeo,Columbus, Ohio.",
        "rating": 4.3,
        "pages": 418,
        "genre": ["Philosophy"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "A short textbook of a Psychiatry 7th edition",
        "author": "Niraj Ahuja",
        "cover": "/shorttextbookofpsychiatry7thed.jpg",
        "description": "A comprehensive guide to psychiatry principles and practices.",
        "rating": 4.2,
        "pages": 273,
        "genre": ["Medicine", "Psychiatry"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Semantics",
        "author": "John I. Saeed",
        "cover": "/semantics.jpg",
        "description": "A comprehensive guide to semantics principles and practices.",
        "rating": 4.3,
        "pages": 437,
        "genre": ["Linguistics", "Semantics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title":" Thomas Culculas 13th edition",
        "author": "George B. Thomas, Jr., Maurice D. Weir, Joel Hass",
        "cover": "/thomascalculus.jpg",
        "description": "A comprehensive guide to calculus principles and practices.",
        "rating": 4.4,
        "pages": 1205,
        "genre": ["Mathematics", "Calculus"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Linear Algebra and Its Applications 5th edition",
        "author": "David C. Lay, Steven R. Lay, Judi J. McDonald",
        "cover": "/linealgebra5thed.jpg",
        "description": "A comprehensive guide to linear algebra principles and practices.",
        "rating": 4.3,
        "pages": 579,
        "genre": ["Mathematics", "Linear Algebra"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Linear Algebra and Its Applications 4th edition",
        "author": "Gilbert Strang",
        "cover": "/linealgebra4thed.webp",
        "description": "A comprehensive guide to linear algebra principles and practices.",
        "rating": 4.3,
        "pages": 545,
        "genre": ["Mathematics", "Linear Algebra"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title":" An Introduction to Statistical Methods and Data Analysis 7th edition",
        "author": "R. Lyman Ott, Michael Longnecker",
        "cover": "/introductiontostatisticalmethods7th.webp",
        "description": "A comprehensive guide to statistical methods and data analysis.",
        "rating": 4.2,
        "pages": 1192,
        "genre": ["Mathematics", "Statistics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "An Introduction to Statistical Methods and Data Analysis 6th edition",
        "author": "R. Lyman Ott, Michael Longnecker",
        "cover": "/introductiontostatisticalmethods6th.jpg",
        "description": "A comprehensive guide to statistical methods and data analysis.",
        "rating": 4.2,
        "pages": 1297,
        "genre": ["Mathematics", "Statistics"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Elementary Differential Equations and Boundary Value Problems 7th edition",
        "author": "William E. Boyce, Richard C. DiPrima",
        "cover": "/elementarydifferentialequations7thed.jpg",
        "description": "A comprehensive guide to elementary differential equations and boundary value problems.",
        "rating": 4.3,
        "pages": 761,
        "genre": ["Mathematics", "Differential Equations"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Elementary Differential Equations and Boundary Value Problems 11th edition",
        "author": "William E. Boyce, Richard C. DiPrima",
        "cover": "/elementarydifferentialequations11thed.webp",
        "description": "A comprehensive guide to elementary differential equations and boundary value problems.",
        "rating": 4.3,
        "pages": 1120,
        "genre": ["Mathematics", "Differential Equations"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      },
      {
        "title": "Elementary Differential Equations and Boundary Value Problems 8th edition",
        "author": "William E. Boyce, Richard C. DiPrima",
        "cover": "/elementarydifferentialequations8thed.jpg",
        "description": "A comprehensive guide to elementary differential equations and boundary value problems.",
        "rating": 4.3,
        "pages": 806,
        "genre": ["Mathematics", "Differential Equations"],
        "source_type": "pdf",
        "content_text": "Sample content...",
        "mime_type": "application/pdf",
        "source_url": None,
        "source_path": None
      }
]

def find_existing_book(db: Session, item: dict) -> Book | None:
    """
    Find an existing book.

    Priority:
    1. Match by source_url if the book has a source_url.
    2. Otherwise match by title + author.
    """

    source_url = item.get("source_url")

    if source_url:
        return db.execute(
            select(Book).where(Book.source_url == source_url)
        ).scalar_one_or_none()

    return db.execute(
        select(Book).where(
            Book.title == item["title"],
            Book.author == item["author"],
        )
    ).scalar_one_or_none()


def apply_book_seed_data(book: Book, item: dict) -> None:
    """
    Apply seed data to a Book model.

    This works for both new books and existing books.
    """

    book.title = item["title"]
    book.author = item["author"]
    book.cover = item["cover"]
    book.description = item["description"]
    book.rating = item["rating"]
    book.pages = item["pages"]

    book.source_type = item.get("source_type")
    book.content_text = item.get("content_text")
    book.mime_type = item.get("mime_type")
    book.source_url = item.get("source_url")
    book.source_path = item.get("source_path")

    book.genres = item.get("genre", [])


def seed() -> None:
    """Create a realistic, repeatable development dataset.

    The seed is additive/idempotent: it updates the canonical books and creates
    deterministic users, settings, library activity, connections and circles
    without dropping tables or deleting developer data.
    """
    from datetime import date, datetime, timedelta, timezone

    from app.core.security import hash_password
    from app.models.circle import Circle
    from app.models.circle_book import CircleBook
    from app.models.circle_member import CircleMember
    from app.models.circle_progress_update import CircleProgressUpdate
    from app.models.admin_activity_log import AdminActivityLog
    from app.models.library_item import LibraryItem
    from app.models.user import User
    from app.models.user_connection import UserConnection
    from app.models.user_settings import UserSettings

    password = "LibrarianDev!2026"
    now = datetime.now(timezone.utc)

    demo_users = [
        {"full_name": "Librarian Admin", "email": "admin@librarian.local", "role": "ADMIN", "plan": "professional", "avatar_url": None},
        {"full_name": "Demo Reader", "email": "reader@librarian.local", "role": "USER", "plan": "free", "avatar_url": None},
        {"full_name": "Grace Mwangi", "email": "grace@librarian.local", "role": "USER", "plan": "professional", "avatar_url": None},
        {"full_name": "Daniel Otieno", "email": "daniel@librarian.local", "role": "USER", "plan": "free", "avatar_url": None},
        {"full_name": "Amina Hassan", "email": "amina@librarian.local", "role": "USER", "plan": "professional", "avatar_url": None},
        {"full_name": "Samuel Kibet", "email": "samuel@librarian.local", "role": "USER", "plan": "free", "avatar_url": None},
    ]

    with SessionLocal() as db:
        created_users = updated_users = 0
        for item in demo_users:
            user = db.scalar(select(User).where(User.email == item["email"]))
            if user is None:
                user = User(email=item["email"], password_hash=hash_password(password))
                db.add(user)
                created_users += 1
            else:
                updated_users += 1
            user.full_name = item["full_name"]
            user.role = item["role"]
            user.plan = item["plan"]
            user.avatar_url = item["avatar_url"]
            user.is_active = True

        db.flush()

        users = {u.email: u for u in db.scalars(select(User)).all() if u.email.endswith("@librarian.local")}
        admin = users["admin@librarian.local"]
        reader = users["reader@librarian.local"]
        grace = users["grace@librarian.local"]
        daniel = users["daniel@librarian.local"]
        amina = users["amina@librarian.local"]
        samuel = users["samuel@librarian.local"]

        created_books = updated_books = 0
        for item in BOOK_SEED:
            book = find_existing_book(db, item)
            if book is None:
                book = Book()
                created_books += 1
            else:
                updated_books += 1
            apply_book_seed_data(book, item)
            book.visibility = "published"
            book.archived_at = None
            book.is_featured = False
            book.language = "en"
            book.original_format = "born-digital"
            book.rights_statement = "all-rights-reserved"
            db.add(book)

        db.flush()
        books = db.scalars(select(Book).order_by(Book.id)).all()
        if not books:
            raise RuntimeError("No books exist after seeding")

        featured = next((b for b in books if b.title == "Mere Christianity"), books[0])
        featured.is_featured = True

        # Deterministic user preferences make recommendations and onboarding testable.
        preference_map = {
            reader.email: (["Christianity", "Faith"], ["Spiritual Growth", "Focused Reading"], ["Devotional", "Classic"], ["Medium books", "Deep books"], "5 books/week", True),
            grace.email: (["Productivity", "Technology"], ["Career", "Deep Learning"], ["Practical", "Modern"], ["Medium books", "Deep books"], "3 books/week", True),
            daniel.email: (["History", "Biography"], ["Knowledge", "Leadership"], ["Narrative"], ["Medium books"], "2 books/week", True),
            amina.email: (["Christianity", "Psychology"], ["Spiritual Growth", "Personal Growth"], ["Devotional", "Reflective"], ["Short reads", "Medium books"], "4 books/week", True),
            samuel.email: (["Productivity", "Science"], ["Learning", "Focus"], ["Practical"], ["Short reads", "Medium books"], "3 books/week", False),
            admin.email: (["Archive", "History"], ["Research", "Discovery"], ["Scholarly"], ["Deep books"], "5 books/week", True),
        }
        for email, values in preference_map.items():
            user = users[email]
            settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            if settings is None:
                settings = UserSettings(user_id=user.id)
            settings.theme = "dark"
            settings.density = "comfortable"
            settings.reading_mode = "scroll"
            settings.font_size = "medium"
            settings.line_height = "comfortable"
            settings.auto_bookmark = True
            settings.show_progress_bar = True
            settings.email_updates = True
            settings.reading_reminders = True
            settings.product_announcements = email == admin.email
            settings.profile_visibility = "friends" if email in {grace.email, amina.email} else "private"
            settings.share_reading_activity = email in {reader.email, grace.email, amina.email}
            settings.preferred_genres = values[0]
            settings.reading_goals = values[1]
            settings.content_styles = values[2]
            settings.preferred_lengths = values[3]
            settings.weekly_target = values[4]
            settings.onboarding_completed = values[5]
            db.add(settings)

        # Library activity: saved, reading and finished states with realistic progress.
        def upsert_library(user: User, book: Book, status: str, progress: int, current_page: int | None = None, bookmark_page: int | None = None, days_ago: int = 1) -> LibraryItem:
            item = db.scalar(select(LibraryItem).where(LibraryItem.user_id == user.id, LibraryItem.book_id == book.id))
            if item is None:
                item = LibraryItem(user_id=user.id, book_id=book.id)
            item.status = status
            item.progress = progress
            item.total_pages = book.pages
            item.current_page = current_page
            item.bookmark_page = bookmark_page
            item.last_read_at = now - timedelta(days=days_ago) if status == "reading" else item.last_read_at
            item.finished_at = now - timedelta(days=days_ago) if status == "finished" else None
            db.add(item)
            return item

        picks = {
            reader: [(0, "reading", 42), (1, "finished", 100), (6, "saved", 0), (15, "saved", 0), (20, "reading", 68)],
            grace: [(10, "reading", 55), (11, "finished", 100), (2, "saved", 0), (17, "saved", 0)],
            daniel: [(3, "finished", 100), (8, "reading", 31), (12, "saved", 0)],
            amina: [(4, "reading", 76), (7, "finished", 100), (9, "saved", 0)],
            samuel: [(10, "saved", 0), (14, "reading", 24), (18, "saved", 0)],
            admin: [(0, "finished", 100), (5, "reading", 63), (9, "saved", 0)],
        }
        for user, rows in picks.items():
            for idx, status, progress in rows:
                if idx >= len(books):
                    continue
                book = books[idx]
                page = max(1, round(book.pages * progress / 100)) if progress else None
                upsert_library(user, book, status, progress, page, page, 2 if status == "reading" else 8)

        # Accepted, pending and declined connection states.
        connection_specs = [
            (reader, grace, "accepted", "friend"),
            (reader, daniel, "accepted", "mentor"),
            (reader, amina, "pending", "friend"),
            (samuel, reader, "pending", "school"),
            (grace, samuel, "declined", "friend"),
        ]
        for requester, addressee, status, relationship_type in connection_specs:
            row = db.scalar(select(UserConnection).where(UserConnection.requester_id == requester.id, UserConnection.addressee_id == addressee.id))
            if row is None:
                row = UserConnection(requester_id=requester.id, addressee_id=addressee.id)
            row.status = status
            row.relationship_type = relationship_type
            db.add(row)

        db.flush()

        # Circles with owners, members, books and progress.
        circle_specs = [
            ("Deep Reading Circle", "deep-reading-circle", "A focused group for slow, thoughtful reading and weekly discussion.", "private", reader),
            ("Faith & Formation", "faith-and-formation", "Shared reading around Christian faith, Scripture, spiritual formation and discipleship.", "private", grace),
            ("Archive Explorers", "archive-explorers", "Discovering historical, cultural and scholarly works across the archive.", "public", admin),
        ]
        circles = {}
        for name, slug, description, visibility, owner in circle_specs:
            circle = db.scalar(select(Circle).where(Circle.slug == slug))
            if circle is None:
                circle = Circle(name=name, slug=slug, owner_id=owner.id)
            circle.name = name
            circle.description = description
            circle.visibility = visibility
            circle.owner_id = owner.id
            circle.archived_at = None
            db.add(circle)
            db.flush()
            circles[slug] = circle

        member_specs = [
            (circles["deep-reading-circle"], reader, "owner", reader),
            (circles["deep-reading-circle"], grace, "member", reader),
            (circles["deep-reading-circle"], daniel, "member", reader),
            (circles["faith-and-formation"], grace, "owner", grace),
            (circles["faith-and-formation"], reader, "member", grace),
            (circles["faith-and-formation"], amina, "member", grace),
            (circles["archive-explorers"], admin, "owner", admin),
            (circles["archive-explorers"], reader, "member", admin),
            (circles["archive-explorers"], daniel, "member", admin),
            (circles["archive-explorers"], samuel, "member", admin),
        ]
        for circle, user, role, inviter in member_specs:
            member = db.scalar(select(CircleMember).where(CircleMember.circle_id == circle.id, CircleMember.user_id == user.id))
            if member is None:
                member = CircleMember(circle_id=circle.id, user_id=user.id)
            member.role = role
            member.status = "active"
            member.invited_by_user_id = None if user.id == circle.owner_id else inviter.id
            member.joined_at = now - timedelta(days=14 if role == "owner" else 7)
            db.add(member)

        db.flush()
        circle_book_specs = [
            ("deep-reading-circle", 0, "A four-week deep reading of Lewis.", 21),
            ("deep-reading-circle", 1, "A practical follow-up read.", 14),
            ("faith-and-formation", 2, "Reading toward a deeper life with God.", 28),
            ("faith-and-formation", 8, "Exploring the heart of Christ.", 21),
            ("archive-explorers", 3, "Evidence, history and primary-source thinking.", 30),
            ("archive-explorers", 10, "A productivity classic for focused work.", 21),
        ]
        circle_books = []
        for slug, idx, description, duration in circle_book_specs:
            if idx >= len(books):
                continue
            circle = circles[slug]
            book = books[idx]
            row = db.scalar(select(CircleBook).where(CircleBook.circle_id == circle.id, CircleBook.book_id == book.id))
            if row is None:
                row = CircleBook(circle_id=circle.id, book_id=book.id, created_by_user_id=circle.owner_id)
            row.description = description
            row.start_date = date.today() - timedelta(days=7)
            row.target_end_date = date.today() + timedelta(days=duration)
            row.status = "active"
            db.add(row)
            db.flush()
            circle_books.append(row)

        # Progress events intentionally create a timeline, useful for the circle UI.
        for row in circle_books:
            existing = db.scalar(select(CircleProgressUpdate).where(CircleProgressUpdate.circle_book_id == row.id, CircleProgressUpdate.user_id == reader.id))
            if existing is None:
                library_item = db.scalar(select(LibraryItem).where(LibraryItem.user_id == reader.id, LibraryItem.book_id == row.book_id))
                if library_item:
                    db.add(CircleProgressUpdate(
                        circle_id=row.circle_id,
                        circle_book_id=row.id,
                        user_id=reader.id,
                        library_item_id=library_item.id,
                        progress_percent=min(library_item.progress, 100),
                        current_page=library_item.current_page,
                        bookmark_page=library_item.bookmark_page,
                        note="Making steady progress — sharing this update with the circle.",
                        visibility="circle",
                        created_at=now - timedelta(days=1),
                    ))

        # A small admin activity trail makes the admin dashboard useful immediately.
        actions = [
            ("seed.dataset_created", "dataset", None),
            ("book.featured", "book", featured.id),
            ("circle.created", "circle", circles["deep-reading-circle"].id),
            ("circle.created", "circle", circles["archive-explorers"].id),
        ]
        for action, entity_type, entity_id in actions:
            exists = db.scalar(select(AdminActivityLog).where(AdminActivityLog.action == action, AdminActivityLog.entity_type == entity_type, AdminActivityLog.entity_id == entity_id))
            if exists is None:
                db.add(AdminActivityLog(admin_user_id=admin.id, action=action, entity_type=entity_type, entity_id=entity_id, metadata_json={"source": "seed_db"}))

        # Notification inbox state makes realtime/mobile testing meaningful immediately.
        notification_specs = [
            (reader, "connection.request", "New connection request", "Amina Hassan wants to connect with you.", {"connection_id": None, "user_id": amina.id}, False),
            (reader, "circle.activity", "Deep Reading Circle", "Your circle has new reading activity around Mere Christianity.", {"circle_slug": "deep-reading-circle"}, False),
            (reader, "reading.reminder", "Keep your reading momentum", "You have books in progress waiting for you.", {"route": "/library"}, True),
            (grace, "connection.accepted", "Connection accepted", "John Reader accepted your connection request.", {"user_id": reader.id}, False),
            (grace, "circle.activity", "Faith & Formation", "Your circle has an active reading discussion.", {"circle_slug": "faith-and-formation"}, False),
            (amina, "circle.invite", "Circle invitation", "Grace Reader added you to Faith & Formation.", {"circle_slug": "faith-and-formation"}, False),
            (admin, "system.info", "Development environment ready", "The Librarian development dataset has been seeded successfully.", {"source": "seed_db"}, True),
        ]
        for user, type_, title, body, data, is_read in notification_specs:
            exists = db.scalar(select(Notification).where(
                Notification.user_id == user.id,
                Notification.type == type_,
                Notification.title == title,
            ))
            if exists is None:
                db.add(Notification(
                    user_id=user.id,
                    type=type_,
                    title=title,
                    body=body,
                    data_json=data,
                    read_at=now - timedelta(days=1) if is_read else None,
                    created_at=now - timedelta(hours=6),
                ))

        db.commit()

        counts = {}
        for table in ["users", "books", "library_items", "user_connections", "circles", "circle_members", "circle_books", "circle_progress_updates", "user_settings", "admin_activity_logs", "notifications"]:
            counts[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()

        print("Database connection confirmed")
        print("Powerful development seed complete")
        print(f"Demo login password: {password}")
        print(f"Created users: {created_users}; existing users reused: {updated_users}")
        print(f"Created books: {created_books}; updated books: {updated_books}")
        for table, count in counts.items():
            print(f"{table}: {count}")


if __name__ == "__main__":
    seed()
