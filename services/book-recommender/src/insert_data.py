import sqlite3
import os

print(f"Current working directory: {os.getcwd()}")
db_path = "library.db"

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print(f"✓ Connected to database: {db_path}")
except Exception as e:
    print(f"✗ Failed to connect to database: {e}")
    exit(1)

books = [
    # Python
('B001', 'Python for Data Analysis', 'Wes McKinney', 'Programming', 2017, 'Focuses on data analysis using Python libraries like pandas and NumPy, ideal for data scientists and analysts.'),
('B002', 'Learning Python', 'Mark Lutz', 'Programming', 2013, 'Comprehensive guide covering Python fundamentals, syntax, and advanced programming concepts for beginners and professionals.'),
('B003', 'Fluent Python', 'Luciano Ramalho', 'Programming', 2015, 'Deep dive into Python features, best practices, and writing efficient, idiomatic Python code.'),
('B004', 'Automate the Boring Stuff with Python', 'Al Sweigart', 'Programming', 2019, 'Beginner-friendly book teaching automation of everyday tasks using Python scripting.'),
('B005', 'Effective Python', 'Brett Slatkin', 'Programming', 2020, 'Provides practical tips and best practices to write clean, efficient, and maintainable Python code.'),

# Java
('B006', 'Java The Complete Reference', 'Herbert Schildt', 'Programming', 2021, 'Comprehensive reference covering core Java concepts, APIs, and advanced programming techniques.'),
('B007', 'Effective Java', 'Joshua Bloch', 'Programming', 2018, 'Best practices and design patterns for writing robust and maintainable Java applications.'),
('B008', 'Java: A Beginner Guide', 'Herbert Schildt', 'Programming', 2019, 'Introductory guide explaining Java basics with examples for new programmers.'),
('B009', 'Core Java Volume I', 'Cay Horstmann', 'Programming', 2020, 'Detailed explanation of Java fundamentals including OOP concepts and standard libraries.'),
('B010', 'Head First Java', 'Kathy Sierra', 'Programming', 2005, 'Interactive and visual approach to learning Java concepts for beginners.'),

# JavaScript
('B011', 'JavaScript Bible', 'Danny Goodman', 'Programming', 2010, 'Comprehensive guide covering JavaScript fundamentals, DOM manipulation, and web scripting techniques.'),
('B012', 'Eloquent JavaScript', 'Marijn Haverbeke', 'Programming', 2018, 'Modern introduction to JavaScript, programming concepts, and functional programming techniques.'),
('B013', 'You Don’t Know JS', 'Kyle Simpson', 'Programming', 2015, 'In-depth exploration of JavaScript core mechanisms like closures, scope, and asynchronous programming.'),
('B014', 'JavaScript: The Good Parts', 'Douglas Crockford', 'Programming', 2008, 'Highlights the most effective and reliable features of JavaScript for building robust applications.'),
('B015', 'Learning JavaScript Design Patterns', 'Addy Osmani', 'Programming', 2012, 'Explains reusable design patterns and best practices for scalable JavaScript development.'),

# Data Structures
('B016', 'Fundamentals of Data Structures in C', 'Horowitz', 'Data Structures', 2008, 'Covers fundamental data structures like stacks, queues, trees, and graphs using C language.'),
('B017', 'Data Structures Using C', 'Reema Thareja', 'Data Structures', 2014, 'Provides detailed explanations and implementations of data structures using C programming.'),
('B018', 'Classic Data Structures', 'Debasis Samanta', 'Data Structures', 2009, 'Introduces classical data structures and algorithms with problem-solving techniques.'),
('B019', 'Data Structures and Algorithms in C', 'Mark Allen Weiss', 'Data Structures', 2013, 'Explains data structures along with algorithm design and analysis concepts.'),
('B020', 'Algorithms in C', 'Robert Sedgewick', 'Data Structures', 2011, 'Focuses on algorithm design, analysis, and implementation using C.'),

# Software Testing
('B021', 'Software Testing Principles and Practice', 'Naresh Chauhan', 'Software Testing', 2010, 'Covers fundamentals of software testing, methodologies, and practical testing approaches.'),
('B022', 'Software Testing: A Craftsman Approach', 'Paul Jorgensen', 'Software Testing', 2013, 'Detailed study of testing techniques, strategies, and quality assurance practices.'),
('B023', 'Foundations of Software Testing', 'Rex Black', 'Software Testing', 2012, 'Provides a strong foundation in testing concepts, lifecycle, and defect management.'),
('B024', 'Introduction to Software Testing', 'Ammann & Offutt', 'Software Testing', 2016, 'Explains testing techniques, automation, and coverage criteria.'),
('B025', 'Practical Software Testing', 'Ilene Burnstein', 'Software Testing', 2002, 'Focuses on real-world testing practices and quality improvement techniques.'),

# OS
('B026', 'Operating System Concepts', 'Abraham Silberschatz', 'Operating Systems', 2018, 'Covers core OS concepts such as processes, memory management, and file systems.'),
('B027', 'Modern Operating Systems', 'Andrew Tanenbaum', 'Operating Systems', 2014, 'Provides detailed understanding of modern OS design and implementation.'),
('B028', 'Operating Systems: Three Easy Pieces', 'Remzi Arpaci-Dusseau', 'Operating Systems', 2018, 'Simplifies OS concepts with practical examples and easy explanations.'),
('B029', 'Linux Kernel Development', 'Robert Love', 'Operating Systems', 2010, 'Focuses on Linux kernel architecture and development concepts.'),
('B030', 'Understanding Operating Systems', 'Ann McHoes', 'Operating Systems', 2012, 'Explains OS fundamentals with real-world examples.'),

# AI
('B031', 'Artificial Intelligence: A Modern Approach', 'Russell Norvig', 'Artificial Intelligence', 2020, 'Comprehensive introduction to AI concepts including search, reasoning, and machine learning.'),
('B032', 'Machine Learning', 'Tom Mitchell', 'Artificial Intelligence', 1997, 'Classic book explaining fundamental machine learning concepts and algorithms.'),
('B033', 'Deep Learning', 'Ian Goodfellow', 'Artificial Intelligence', 2016, 'Detailed coverage of neural networks and deep learning techniques.'),
('B034', 'AI Superpowers', 'Kai-Fu Lee', 'Artificial Intelligence', 2018, 'Discusses the impact of AI on society and global technological competition.'),
('B035', 'Pattern Recognition and Machine Learning', 'Christopher Bishop', 'Artificial Intelligence', 2006, 'Mathematical approach to machine learning and pattern recognition.'),

# PHP
('B036', 'PHP: The Complete Reference', 'Steven Holzner', 'Web Development', 2007, 'Covers PHP programming fundamentals and web development techniques.'),
('B037', 'Learning PHP, MySQL & JavaScript', 'Robin Nixon', 'Web Development', 2018, 'Full-stack web development using PHP, MySQL, and JavaScript.'),
('B038', 'Modern PHP', 'Josh Lockhart', 'Web Development', 2015, 'Focuses on modern PHP practices and frameworks.'),
('B039', 'PHP Objects, Patterns, and Practice', 'Matt Zandstra', 'Web Development', 2016, 'Advanced PHP concepts including OOP and design patterns.'),
('B040', 'Head First PHP & MySQL', 'Lynn Beighley', 'Web Development', 2009, 'Beginner-friendly introduction to PHP and MySQL.'),

# Cloud
('B041', 'Cloud Computing Principles and Paradigms', 'Rajkumar Buyya', 'Cloud Computing', 2011, 'Explains cloud computing architecture, models, and applications.'),
('B042', 'Cloud Computing: Concepts and Design', 'Thomas Erl', 'Cloud Computing', 2013, 'Covers cloud design principles and service models.'),
('B043', 'Architecting the Cloud', 'Michael J Kavis', 'Cloud Computing', 2014, 'Guidelines for designing scalable cloud systems.'),
('B044', 'Cloud Native DevOps', 'John Arundel', 'Cloud Computing', 2021, 'Focuses on DevOps practices in cloud-native environments.'),
('B045', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 'Cloud Computing', 2017, 'Explains distributed systems and scalable data architectures.'),

# MySQL
('B046', 'MySQL', 'Paul DuBois', 'Databases', 2015, 'Comprehensive guide to MySQL database management and SQL queries.'),
('B047', 'Learning MySQL', 'Seyed Tahaghoghi', 'Databases', 2007, 'Beginner guide to MySQL concepts and database design.'),
('B048', 'High Performance MySQL', 'Baron Schwartz', 'Databases', 2012, 'Advanced techniques for optimizing MySQL performance.'),
('B049', 'SQL Cookbook', 'Anthony Molinaro', 'Databases', 2020, 'Collection of SQL recipes for solving common database problems.'),
('B050', 'Database System Concepts', 'Silberschatz', 'Databases', 2019, 'Fundamental concepts of database systems and design.'),

# Wireless
('B051', 'Wireless Communications', 'Andreas Molisch', 'Electronics', 2012, 'Detailed study of wireless communication systems and technologies.'),
('B052', 'Wireless Communication Systems', 'Ke-Lin Du', 'Electronics', 2010, 'Explains principles and applications of wireless systems.'),
('B053', 'Fundamentals of Wireless Communication', 'David Tse', 'Electronics', 2005, 'Covers theoretical foundations of wireless communication.'),
('B054', 'Mobile Communications', 'Jochen Schiller', 'Electronics', 2012, 'Focuses on mobile communication technologies and protocols.'),
('B055', '5G NR', 'Erik Dahlman', 'Electronics', 2018, 'Explains 5G network architecture and standards.'),

# Hadoop
('B056', 'Hadoop in Action', 'Chuck Lam', 'Big Data', 2010, 'Introduction to Hadoop ecosystem and distributed data processing.'),
('B057', 'Hadoop: The Definitive Guide', 'Tom White', 'Big Data', 2015, 'Comprehensive guide to Hadoop framework and tools.'),
('B058', 'Data-Intensive Text Processing with MapReduce', 'Jimmy Lin', 'Big Data', 2010, 'Explains MapReduce techniques for large-scale data processing.'),
('B059', 'Spark: The Definitive Guide', 'Bill Chambers', 'Big Data', 2018, 'Covers Apache Spark for big data processing and analytics.'),
('B060', 'Streaming Systems', 'Tyler Akidau', 'Big Data', 2018, 'Focuses on real-time data processing systems.'),

# MongoDB
('B061', 'MongoDB: The Definitive Guide', 'Shannon Bradshaw', 'Databases', 2019, 'Comprehensive guide to MongoDB database and NoSQL concepts.'),
('B062', 'MongoDB Basics', 'Peter Membrey', 'Databases', 2010, 'Beginner-friendly introduction to MongoDB.'),
('B063', 'Practical MongoDB', 'Shakuntala Gupta', 'Databases', 2014, 'Practical applications and usage of MongoDB.'),
('B064', 'NoSQL Distilled', 'Pramod Sadalage', 'Databases', 2012, 'Explains NoSQL databases and their use cases.'),
('B065', 'Seven Databases in Seven Weeks', 'Eric Redmond', 'Databases', 2012, 'Overview of different database systems including NoSQL.'),

# HCI
('B066', 'HCI', 'Rajendra Kumar', 'Human Computer Interaction', 2010, 'Introduction to human-computer interaction concepts and usability principles.'),
('B067', 'A Practical Guide to HCI', 'Stephan', 'Human Computer Interaction', 2012, 'Practical approaches to designing user interfaces.'),
('B068', 'Designing the User Interface', 'Ben Shneiderman', 'Human Computer Interaction', 2016, 'Principles of user interface design and usability.'),
('B069', 'The Design of Everyday Things', 'Don Norman', 'Human Computer Interaction', 2013, 'Explains user-centered design and usability concepts.'),
('B070', 'Interaction Design', 'Preece Rogers Sharp', 'Human Computer Interaction', 2019, 'Comprehensive guide to interaction design and user experience.'),
]

try:
    cur.executemany("""
INSERT INTO books (book_id, title, author, category, year, summary)
VALUES (?, ?, ?, ?, ?, ?)
""", books)
    conn.commit()
    print(f"✓ Successfully inserted {len(books)} books into the database")
except Exception as e:
    print(f"✗ Failed to insert books: {e}")
    conn.rollback()
finally:
    conn.close()
    print("✓ Database connection closed")
