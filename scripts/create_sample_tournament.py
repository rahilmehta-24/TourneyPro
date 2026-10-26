"""Create Sample Tournament Script for TourneyPro.

Specifications:
- 6 different categories:
  1. Boys U-14 Singles (Single Elimination)
  2. Boys U-16 Singles (Single Elimination)
  3. Boys U-18 Singles (Single Elimination)
  4. Girls Open Championship (Group Stage: 8 Groups of 4 = 32 players)
  5. Men's Open Singles (Single Elimination)
  6. Men's Open Doubles (Single Elimination)
- Every category has AT LEAST 32 players (Counts: 33, 33, 33, 32, 33, 32)
- Total unique players: 140
  - Exactly 15.0% (21 players) in 3 categories
  - Exactly 10.0% (14 players) in 2 categories
  - Exactly 75.0% (105 players) in 1 category
- Randomized payment methods ('Online - Paid', 'Cash - Paid', 'Online - Pending', 'Cash - Pending', 'Free')
"""

import random
from datetime import date
from app import create_app
from app.domain.models import (
    db,
    User,
    Tournament,
    Category,
    Player,
    Participant,
    Registration,
    Group,
)

random.seed(101)

FIRST_NAMES_MALE = [
    "Aarav",
    "Vivaan",
    "Aditya",
    "Vihaan",
    "Arjun",
    "Reyansh",
    "Muhammad",
    "Sai",
    "Arnav",
    "Ayaan",
    "Krishna",
    "Ishaan",
    "Shaurya",
    "Atharva",
    "Advik",
    "Pranav",
    "Advaith",
    "Aaryan",
    "Dhruv",
    "Kabir",
    "Rohan",
    "Devansh",
    "Karthik",
    "Siddharth",
    "Yash",
    "Harsh",
    "Neil",
    "Vikram",
    "Sameer",
    "Gaurav",
    "Kunal",
    "Tushar",
    "Farhan",
    "Zaid",
    "Liam",
    "Noah",
    "Oliver",
    "James",
    "Lucas",
    "Mateo",
    "Leo",
    "Jack",
    "Ethan",
    "Daniel",
    "Henry",
    "Alexander",
    "Sebastian",
    "Julian",
    "Dylan",
    "Sam",
    "Rafael",
    "Carlos",
    "Jannik",
    "Daniil",
    "Stefanos",
    "Casper",
    "Holger",
    "Taylor",
    "Hubert",
    "Felix",
    "Lorenzo",
    "Alex",
    "Tommy",
    "Ben",
    "Frances",
    "Sebastian",
    "Denis",
    "Grigor",
    "Milos",
    "Kei",
    "Borna",
    "Marin",
    "Dominic",
    "David",
    "Richard",
    "Stan",
    "Gilles",
    "Jo-Wilfried",
    "Andy",
    "Lleyton",
]

FIRST_NAMES_FEMALE = [
    "Ananya",
    "Diya",
    "Isha",
    "Riya",
    "Avani",
    "Tara",
    "Mira",
    "Saanvi",
    "Aadhya",
    "Kiara",
    "Myra",
    "Sara",
    "Anika",
    "Navya",
    "Arya",
    "Ira",
    "Pari",
    "Meera",
    "Siya",
    "Rhea",
    "Zoya",
    "Kavya",
    "Tanvi",
    "Nisha",
    "Pooja",
    "Shreya",
    "Sneha",
    "Aditi",
    "Neha",
    "Divya",
    "Natasha",
    "Elena",
    "Sofia",
    "Aryna",
    "Iga",
    "Coco",
    "Jessica",
    "Paula",
    "Emma",
    "Ons",
    "Maria",
    "Simona",
    "Karolina",
    "Victoria",
    "Angelique",
    "Petra",
    "Garbiñe",
    "Sloane",
    "Naomi",
    "Ashleigh",
]

LAST_NAMES = [
    "Sharma",
    "Verma",
    "Mehta",
    "Patel",
    "Joshi",
    "Rao",
    "Kulkarni",
    "Deshmukh",
    "Sen",
    "Gupta",
    "Nair",
    "Bhattacharya",
    "Saxena",
    "Malhotra",
    "Iyer",
    "Subramanian",
    "Choudhury",
    "Pandey",
    "Kapoor",
    "Agarwal",
    "Singhania",
    "Bhatia",
    "Nambiar",
    "Hegde",
    "Mishra",
    "Sengupta",
    "Chauhan",
    "Deshpande",
    "Namboodiri",
    "Rathore",
    "Merchant",
    "Soni",
    "Bhasin",
    "Qureshi",
    "Raju",
    "Khan",
    "DSouza",
    "Goswami",
    "Parekh",
    "Chawla",
    "Bannerjee",
    "Sundaram",
    "Kher",
    "Shah",
    "Talreja",
    "OConnell",
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
    "Gomez",
    "Phillips",
    "Evans",
    "Turner",
]

CATEGORIES_CONFIG = [
    {
        "name": "Boys U-14 Singles",
        "gender": "Boys",
        "age_cat": "U14",
        "format": "single_elimination",
        "fee": 500.0,
        "is_group": False,
    },
    {
        "name": "Boys U-16 Singles",
        "gender": "Boys",
        "age_cat": "U16",
        "format": "single_elimination",
        "fee": 600.0,
        "is_group": False,
    },
    {
        "name": "Boys U-18 Singles",
        "gender": "Boys",
        "age_cat": "U18",
        "format": "single_elimination",
        "fee": 700.0,
        "is_group": False,
    },
    {
        "name": "Girls Championship (Group Stage + Knockouts League)",
        "gender": "Girls",
        "age_cat": "Open",
        "format": "group_stage",
        "fee": 600.0,
        "is_group": True,
    },
    {
        "name": "Men's Open Singles (Round Robin League)",
        "gender": "Mens",
        "age_cat": "Open",
        "format": "round_robin",
        "fee": 800.0,
        "is_group": False,
    },
    {
        "name": "Men's Open Doubles",
        "gender": "Mens",
        "age_cat": "Open",
        "format": "doubles_elimination",
        "fee": 1000.0,
        "is_group": False,
    },
]

DOUBLES_PARTNER_NAMES = [
    "Rohan Parekh",
    "Naveen Chawla",
    "Pritam Bannerjee",
    "Harish Sundaram",
    "Anupam Kher",
    "Jayesh Shah",
    "Amitabh Sen",
    "Suraj Talreja",
    "Deepak Verma",
    "Manoj Tiwari",
    "Sanjay Singhania",
    "Kishore Kumar",
    "Sunil Gavaskar",
    "Kapil Dev",
    "Sachin Tendulkar",
    "Rahul Dravid",
    "Sourav Ganguly",
    "VVS Laxman",
    "Anil Kumble",
    "Javagal Srinath",
    "Zaheer Khan",
    "Harbhajan Singh",
    "Yuvraj Singh",
    "MS Dhoni",
    "Suresh Raina",
    "Gautam Gambhir",
    "Virender Sehwag",
    "Rohit Sharma",
    "Virat Kohli",
    "Shikhar Dhawan",
    "Ravindra Jadeja",
    "Ravichandran Ashwin",
    "Jasprit Bumrah",
    "Mohammed Shami",
]


def generate_unique_names(count=140):
    used = set()
    names_male = []
    names_female = []

    # Category 3 is Girls Open (needs at least 32 female players)
    # Generate ~45 female names and ~95 male names
    while len(names_female) < 45:
        fn = random.choice(FIRST_NAMES_FEMALE)
        ln = random.choice(LAST_NAMES)
        full = f"{fn} {ln}"
        if full not in used:
            used.add(full)
            names_female.append(full)

    while len(names_male) < (count - len(names_female)):
        fn = random.choice(FIRST_NAMES_MALE)
        ln = random.choice(LAST_NAMES)
        full = f"{fn} {ln}"
        if full not in used:
            used.add(full)
            names_male.append(full)

    return names_male, names_female


def seed_sample_tournament():
    app = create_app()
    with app.app_context():
        admin = (
            User.query.filter_by(role="superadmin").first()
            or User.query.filter_by(role="admin").first()
        )
        if not admin:
            admin = User(username="admin", email="admin@tourneypro.com", role="superadmin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.flush()

        slug = "national-tennis-championship-2026"

        existing_tourney = Tournament.query.filter_by(url_slug=slug).first()
        if existing_tourney:
            print(f"Removing existing tournament '{slug}'...")
            db.session.delete(existing_tourney)
            db.session.commit()

        # 1. Create Tournament
        tournament = Tournament(
            name="National Tennis Championship 2026",
            url_slug=slug,
            user_id=admin.id,
            status="registration",
            has_categories=True,
            game_info="National Sports Complex, Central Arena (Courts 1-8)",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 18),
            court_names="Center Court, Court 1, Court 2, Court 3, Court 4, Court 5, Court 6, Court 7",
            num_courts=8,
            court_operating_start="08:00",
            court_operating_end="20:00",
        )
        db.session.add(tournament)
        db.session.flush()

        print(f"Created Tournament: '{tournament.name}' (ID: {tournament.id})")

        # 2. Create 6 Categories (including 1 Group Stage category)
        created_categories = []
        group_objects = []

        for cat_cfg in CATEGORIES_CONFIG:
            is_group = cat_cfg["is_group"]
            cat = Category(
                tournament_id=tournament.id,
                name=cat_cfg["name"],
                gender=cat_cfg["gender"],
                age_category=cat_cfg["age_cat"],
                format=cat_cfg["format"],
                entry_fee=cat_cfg["fee"],
                status="setup",
                num_sets=3,
                games_per_set=6,
                has_group_stage=is_group,
                num_groups=8 if is_group else None,
                teams_per_group=4 if is_group else None,
                qualifiers_per_group=2 if is_group else None,
            )
            db.session.add(cat)
            db.session.flush()
            created_categories.append(cat)
            print(
                f"  - Category {cat.id}: {cat.name} (Format: {cat.format}, Fee: ₹{int(cat.entry_fee)})"
            )

            # If Group Stage: Create 8 groups (Group A to Group H)
            if is_group:
                group_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
                for g_idx, letter in enumerate(group_letters):
                    grp = Group(
                        category_id=cat.id,
                        name=f"Group {letter}",
                        assigned_courts=f"Court {(g_idx % 8) + 1}",
                        start_time="09:00" if g_idx < 4 else "13:30",
                    )
                    db.session.add(grp)
                    db.session.flush()
                    group_objects.append(grp)
                print(
                    f"    -> Created {len(group_objects)} groups for {cat.name} (Group A through Group H)"
                )

        # 3. Create 140 Unique Players
        # Target Category Counts:
        # Cat 0 (Boys U-14): 33
        # Cat 1 (Boys U-16): 33
        # Cat 2 (Boys U-18): 33
        # Cat 3 (Girls Open - Group Stage): 32
        # Cat 4 (Men's Open Singles): 33
        # Cat 5 (Men's Open Doubles): 32
        # Total = 196 enrollments.
        #
        # Distribution:
        # 21 players in 3 categories = 63 enrollments (15.0%)
        # 14 players in 2 categories = 28 enrollments (10.0%)
        # 105 players in 1 category   = 105 enrollments (75.0%)
        # Total = 140 unique players, 196 enrollments.

        names_male, names_female = generate_unique_names(140)

        # Build player profiles
        total_unique_players = 140
        players_manifest = []

        # Female players (32 will be in Cat 3 Girls Open, and some in multi-category)
        female_player_objects = []
        for i, name in enumerate(names_female):
            dob_year = random.randint(1995, 2010)
            p = Player(
                name=name,
                contact_number=f"+91 98200{1000 + i:04d}",
                email=f"{name.lower().replace(' ', '.').replace("'", '')}@example.com",
                gender="Female",
                dob=date(dob_year, random.randint(1, 12), random.randint(1, 28)),
                age_category="Open",
            )
            db.session.add(p)
            db.session.flush()
            female_player_objects.append(p)

        male_player_objects = []
        for i, name in enumerate(names_male):
            dob_year = random.randint(1995, 2012)
            age_cat = (
                "U14"
                if dob_year >= 2012
                else ("U16" if dob_year >= 2010 else ("U18" if dob_year >= 2008 else "Open"))
            )
            p = Player(
                name=name,
                contact_number=f"+91 98300{2000 + i:04d}",
                email=f"{name.lower().replace(' ', '.').replace("'", '')}@example.com",
                gender="Male",
                dob=date(dob_year, random.randint(1, 12), random.randint(1, 28)),
                age_category=age_cat,
            )
            db.session.add(p)
            db.session.flush()
            male_player_objects.append(p)

        all_players = female_player_objects + male_player_objects
        # Total players: 140
        assert len(all_players) == 140

        # Exact category slots needed:
        target_counts = {0: 33, 1: 33, 2: 33, 3: 32, 4: 33, 5: 32}
        remaining_slots = dict(target_counts)

        # Track category assignments per player
        player_cat_assignments = {p.id: [] for p in all_players}

        # Step 3A: Assign 21 players to 3 categories (15.0%)
        # 3 female players get 3 categories (Cat 3 + two others or Cat 3 + 4 + 5)
        # 18 male players get 3 categories
        multi_3_players = female_player_objects[:3] + male_player_objects[:18]
        assert len(multi_3_players) == 21

        # Preset compatible combinations for 3-category players
        # E.g. [0, 1, 2], [1, 2, 4], [2, 4, 5], [0, 1, 4], etc.
        three_cat_combos = [
            [0, 1, 2],
            [0, 1, 2],
            [0, 1, 2],
            [1, 2, 4],
            [1, 2, 4],
            [1, 2, 4],
            [2, 4, 5],
            [2, 4, 5],
            [2, 4, 5],
            [0, 1, 4],
            [0, 1, 4],
            [0, 1, 4],
            [1, 2, 5],
            [1, 2, 5],
            [1, 2, 5],
            [2, 4, 5],
            [2, 4, 5],
            [0, 2, 4],
            # 3 female players in Cat 3 + other open events
            [3, 4, 5],
            [3, 4, 5],
            [3, 4, 5],
        ]

        for p, combo in zip(multi_3_players, three_cat_combos):
            player_cat_assignments[p.id] = list(combo)
            for c in combo:
                remaining_slots[c] -= 1

        # Step 3B: Assign 14 players to 2 categories (10.0%)
        # 2 female players (Cat 3 + Cat 4)
        # 12 male players (combos: [0, 1], [1, 2], [4, 5], [2, 4], etc.)
        multi_2_players = female_player_objects[3:5] + male_player_objects[18:30]
        assert len(multi_2_players) == 14

        two_cat_combos = [
            [3, 4],
            [3, 5],  # 2 females
            [0, 1],
            [0, 1],
            [0, 2],
            [0, 2],
            [1, 2],
            [1, 2],
            [1, 4],
            [1, 5],
            [2, 4],
            [2, 5],
            [4, 5],
            [4, 5],
        ]

        for p, combo in zip(multi_2_players, two_cat_combos):
            player_cat_assignments[p.id] = list(combo)
            for c in combo:
                remaining_slots[c] -= 1

        # Step 3C: Assign remaining 105 players to 1 category (75.0%)
        single_players = female_player_objects[5:] + male_player_objects[30:]
        assert len(single_players) == 105
        assert sum(remaining_slots.values()) == 105

        # Cat 3 (Girls Open) remaining needed:
        cat_3_needed = remaining_slots[3]  # Exactly 32 - 3 - 2 = 27
        # We have len(female_player_objects) = 45 -> 45 - 5 = 40 single females
        # Take 27 single females for Cat 3
        single_females_for_cat3 = female_player_objects[5 : 5 + cat_3_needed]
        for p in single_females_for_cat3:
            player_cat_assignments[p.id] = [3]
            remaining_slots[3] -= 1

        # Remaining single players to distribute across cats 0, 1, 2, 4, 5
        remaining_single_players = (
            female_player_objects[5 + cat_3_needed :] + male_player_objects[30:]
        )
        assert len(remaining_single_players) == sum(remaining_slots.values())

        p_idx = 0
        for c in [0, 1, 2, 4, 5]:
            slots = remaining_slots[c]
            for _ in range(slots):
                p = remaining_single_players[p_idx]
                player_cat_assignments[p.id] = [c]
                p_idx += 1
            remaining_slots[c] = 0

        # Verify all remaining slots are 0
        assert all(v == 0 for v in remaining_slots.values())

        # Step 4: Create Registrations and Participants
        payment_choices = [
            ("online", "paid"),
            ("online", "paid"),
            ("online", "paid"),
            ("cash", "paid"),
            ("cash", "paid"),
            ("online", "pending"),
            ("cash", "pending"),
            ("free", "paid"),
        ]

        doubles_partner_idx = 0
        group_stage_participant_idx = 0

        total_participants_created = 0
        actual_category_counts = {c: 0 for c in range(6)}

        # Player map by id
        player_map = {p.id: p for p in all_players}

        for p_id, enrolled_cats in player_cat_assignments.items():
            player = player_map[p_id]

            for cat_idx in enrolled_cats:
                cat = created_categories[cat_idx]
                actual_category_counts[cat_idx] += 1

                p_method, p_status = random.choice(payment_choices)

                # Doubles category (Cat 5)
                partner_name = None
                partner_mob = None
                display_name = player.name
                if cat_idx == 5:
                    partner_name = DOUBLES_PARTNER_NAMES[
                        doubles_partner_idx % len(DOUBLES_PARTNER_NAMES)
                    ]
                    partner_mob = f"+91 98400{3000 + doubles_partner_idx:04d}"
                    doubles_partner_idx += 1
                    display_name = f"{player.name} / {partner_name}"

                # Group Stage category (Cat 3: Girls Open Championship)
                assigned_group_id = None
                if cat_idx == 3:
                    # 32 participants divided across 8 groups (4 participants per group)
                    grp_idx = (group_stage_participant_idx // 4) % 8
                    assigned_group_id = group_objects[grp_idx].id
                    group_stage_participant_idx += 1

                # Random seeding
                seed_num = None
                if random.random() < 0.15:
                    seed_num = random.randint(1, 8)

                participant = Participant(
                    tournament_id=tournament.id,
                    category_id=cat.id,
                    group_id=assigned_group_id,
                    player_id=player.id,
                    name=display_name,
                    mobile=player.contact_number,
                    email=player.email,
                    gender=player.gender,
                    dob=player.dob,
                    partner_name=partner_name,
                    partner_mobile=partner_mob,
                    manual_seed=seed_num,
                    payment_status=p_status,
                    payment_method=p_method,
                    checked_in=(random.random() < 0.4),
                )
                db.session.add(participant)

                reg = Registration(
                    tournament_id=tournament.id,
                    category_id=cat.id,
                    user_id=admin.id,
                    player_id=player.id,
                    partner_name=partner_name,
                    partner_mobile=partner_mob,
                    amount_due=cat.entry_fee,
                    payment_method=p_method,
                    payment_status=p_status,
                    status="approved",
                )
                db.session.add(reg)
                total_participants_created += 1

        db.session.commit()

        # Final Verification
        three_count = sum(1 for cats in player_cat_assignments.values() if len(cats) == 3)
        two_count = sum(1 for cats in player_cat_assignments.values() if len(cats) == 2)
        one_count = sum(1 for cats in player_cat_assignments.values() if len(cats) == 1)

        print("\n" + "=" * 65)
        print("SAMPLE TOURNAMENT CREATION COMPLETE!")
        print("=" * 65)
        print(f"Tournament Name: {tournament.name}")
        print(f"Slug:            {tournament.url_slug}")
        print(f"URL:             /tournaments/{tournament.url_slug}")
        print(f"Export PDF URL:  /tournaments/{tournament.url_slug}/participants/export_pdf")
        print("\nCategory Distribution (Every Category >= 32 Players):")
        for idx, cat in enumerate(created_categories):
            fmt_lbl = (
                f"[{cat.format.upper()}]"
                if cat.format != "group_stage"
                else "[GROUP STAGE: 8 Groups x 4]"
            )
            print(
                f"  {idx + 1}. {cat.name:<26} {fmt_lbl:<28} -> {actual_category_counts[idx]} Players"
            )

        print(f"\nTotal Unique Players: {total_unique_players}")
        print(
            f"  • In 3 categories: {three_count} ({three_count / total_unique_players * 100:.1f}%) [target: ~15%]"
        )
        print(
            f"  • In 2 categories: {two_count} ({two_count / total_unique_players * 100:.1f}%) [target: ~10%]"
        )
        print(
            f"  • In 1 category:   {one_count} ({one_count / total_unique_players * 100:.1f}%) [target: ~75%]"
        )
        print(f"Total Registrations:  {total_participants_created}")
        print("=" * 65)


if __name__ == "__main__":
    seed_sample_tournament()
