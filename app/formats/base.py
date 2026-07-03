class TournamentFormat:
    name: str = "Unknown"
    description: str = ""
    icon: str = "❓"
    min_participants: int = 2

    @classmethod
    def generate(cls, category, participants):
        """
        Generate matches for the category.
        
        Args:
            category: Category model instance
            participants: List of Participant objects
            
        Returns:
            List of dictionaries representing kwargs for Match creation.
        """
        raise NotImplementedError("Subclasses must implement generate()")

    @classmethod
    def advance_match(cls, match, category, winner_id=None):
        """
        Handle match completion (e.g., progressing a winner to the next round, 
        or recalculating group points).
        
        Args:
            match: The Match instance just completed
            category: The Category instance
            winner_id: The ID of the winning participant (if applicable)
        """
        raise NotImplementedError("Subclasses must implement advance_match()")

    @classmethod
    def calculate_final_rankings(cls, category):
        """
        Determine final ranks and assign `final_rank` to participants when the tournament ends.
        
        Args:
            category: The Category instance
        """
        raise NotImplementedError("Subclasses must implement calculate_final_rankings()")
