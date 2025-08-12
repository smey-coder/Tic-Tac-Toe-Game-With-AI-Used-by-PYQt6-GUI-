from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout,
    QComboBox, QMessageBox, QDialog, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QUrl
import sys
import random
from datetime import datetime
import json 
import sqlite3
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtGui import QIcon


# TicTicToc game database
class GameHistoryDB:
    """Manages SQLite database operations for Tic Tac Toe game history."""
    def __init__(self, db_file="game_history.db"):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None #Ensure conn is None on failure

    def _create_table(self):
        """Creates the 'games' table if it doesn't exist."""
        if self.cursor:
            try:
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS games (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mode TEXT,
                        winner TEXT,
                        move_history TEXT, -- Stored as JSON string
                        date TEXT
                    )
                """)
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"Error creating table: {e}")
        else:
            print("No database connection to create table.")

    def insert_game(self, game_data):
        """
        Inserts a new game record into the database.
        game_data is a dictionary like:
        {
            "mode": "Random AI",
            "winner": "O",
            "move_history": [{"row":0, "col":0, "player":"X"}, ...],
            "date": "YYYY-MM-DD HH:MM:SS"
        }
        """
        if not self.conn or not self.cursor:
            print("Database not connected. Cannot insert game.")
            return False

        try:
            #Serialize move_history list to a JSON string
            move_history_json = json.dumps(game_data.get('move_history', []))
            
            self.cursor.execute("""
                INSERT INTO games (mode, winner, move_history, date)
                VALUES (?, ?, ?, ?)
            """, (game_data.get('mode', 'N/A'),
                  game_data.get('winner', 'N/A'),
                  move_history_json,
                  game_data.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error inserting game: {e}")
            return False

    def get_all_games(self):
        """
        Retrieves all game records from the database, ordered by ID descending.
        Returns a list of dictionaries.
        """
        if not self.cursor:
            print("Database not connected. Cannot retrieve games.")
            return []

        try:
            self.cursor.execute("SELECT id, mode, winner, move_history, date FROM games")
            rows = self.cursor.fetchall()
            
            games_list = []
            for row in rows:
                game_id, mode, winner, move_history_json, date_str = row
                
                moves = []
                try:
                    moves = json.loads(move_history_json)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to decode move_history for game ID {game_id}")
                    #Keep moves as empty list or handle as desired
                
                games_list.append({
                    "id": game_id,
                    "mode": mode,
                    "winner": winner,
                    "move_history": moves,
                    "date": date_str
                })
            return games_list
        except sqlite3.Error as e:
            print(f"Error retrieving games: {e}")
            return []
        
    

    def delete_games_by_ids(self, ids):
        """
        Deletes game records by a list of IDs.
        """
        if not self.conn or not self.cursor:
            print("Database not connected. Cannot delete games.")
            return False

        try:
            # Create a placeholder string for the IN clause (e.g., '?, ?, ?')
            placeholders = ','.join('?' for _ in ids)
            self.cursor.execute(f"DELETE FROM games WHERE id IN ({placeholders})", ids)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting games: {e}")
            return False

    def close_connection(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            print("Database connection closed.")

    # History Window 
class HistoryWindow(QDialog):
    """A dialog window to display and manage game history using the GameHistoryDB."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game History")
        self.setGeometry(200, 200, 800, 600)
        self.setStyleSheet("background-color: #282c34; color: white;")

        self.db_manager = GameHistoryDB() # Create an instance of the database manager

        self.init_ui()
        self.load_history()

    def closeEvent(self, event):
        """Overrides the close event to ensure database connection is closed."""
        self.db_manager.close_connection()
        super().closeEvent(event)

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Table for history display
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["ID", "Mode", "Winner", "Move History", "Date"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #3e4451;
                color: white;
                gridline-color: #555;
                border: 1px solid #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #4a4f5c;
                color: white;
                padding: 5px;
                border: 1px solid #555;
            }
        """)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.history_table)

        # Buttons for actions
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Current Game")
        self.delete_btn = QPushButton("🗑 Delete Selected")
        self.refresh_btn = QPushButton("🔄 Refresh Data")

        for btn in [self.save_btn, self.delete_btn, self.refresh_btn]:
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #61afef;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #52a0e0;
                }
                QPushButton:pressed {
                    background-color: #4391d1;
                }
            """)
            button_layout.addWidget(btn)

        self.save_btn.clicked.connect(self.save_current_game_to_db)
        self.delete_btn.clicked.connect(self.delete_selected_games)
        self.refresh_btn.clicked.connect(self.load_history)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    

    def load_history(self):
        """
        Loads game history from the SQLite database using GameHistoryDB.
        """
        self.history_table.setRowCount(0) # Clear existing rows
        games = self.db_manager.get_all_games() # Get data from DB manager
        
        for idx, game in enumerate(games):
            self.history_table.insertRow(idx)
            self.history_table.setItem(idx, 0, QTableWidgetItem(str(game["id"])))
            self.history_table.setItem(idx, 1, QTableWidgetItem(game.get("mode", "N/A")))
            self.history_table.setItem(idx, 2, QTableWidgetItem(game.get("winner", "N/A")))
            
            # Format move_history for display
            moves_display = ", ".join([f"{m['player']}:({m['row']},{m['col']})" for m in game.get("move_history", [])])
            self.history_table.setItem(idx, 3, QTableWidgetItem(moves_display))
            
            date_str = game.get("date", "N/A")
            self.history_table.setItem(idx, 4, QTableWidgetItem(date_str))

    def save_current_game_to_db(self):
        """
        This method is connected to the "Save Current Game" button in the HistoryWindow.
        It saves the *last completed game* from the main TicTacToe window using GameHistoryDB.
        """
        parent_game = self.parent() # Access the main TicTacToe window
        if hasattr(parent_game, 'last_game_data') and parent_game.last_game_data:
            if self.db_manager.insert_game(parent_game.last_game_data): # Insert using DB manager
                parent_game.last_game_data = None # Clear after saving
                QMessageBox.information(self, "Save Game", "Last game saved successfully!")
                self.load_history() # Refresh table after saving
            else:
                QMessageBox.critical(self, "Save Game Error", "Failed to save game to database.")
        else:
            QMessageBox.warning(self, "Save Game", "No completed game data to save.")

    def delete_selected_games(self):
        """
        Deletes selected games from the SQLite database using GameHistoryDB.
        """
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Delete", "Please select rows to delete.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete the selected game(s)?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        game_ids_to_delete = []
        for index in selected_rows:
            game_id = self.history_table.item(index.row(), 0).text()
            game_ids_to_delete.append(int(game_id))
        
        if self.db_manager.delete_games_by_ids(game_ids_to_delete): # Delete using DB manager
            QMessageBox.information(self, "Success", "Selected game(s) deleted!")
            self.load_history() # Refresh table after deleting
        else:
            QMessageBox.critical(self, "Delete Error", "Failed to delete game(s) from database.")


class TicTacToeGame(QWidget):
    """The main Tic Tac Toe game window."""
    def __init__(self):
        super().__init__() 
        #Game_sound
        try:
            self.game_sound = QSoundEffect()
            self.game_sound.setSource(QUrl.fromLocalFile(r"c:\Users\85512\Downloads\game-music-loop-6-144641 (online-audio-converter.com).wav"))
            self.game_sound.setVolume(0.5)
            self.game_sound.play()
        except Exception as e:
            QMessageBox.warning(self, "Sound Error", f"Could not load sound file: {e}")

        self.setWindowTitle("Tic Tac Toe")
        self.setStyleSheet("background-color: #1e1e2f;")
        self.current_player = "X"
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        self.mode = "Random AI"
        self._game_moves = [] #To store moves for the current game
        self.last_game_data = None #To hold data of the last completed game for saving

        self.init_ui()
        self.init_sounds()

    #Sound
    def init_sounds(self):
        try:
            #Win sound
            self.win_sound = QSoundEffect()
            self.win_sound.setSource(QUrl.fromLocalFile(r"c:\Users\85512\Downloads\game-win-36082 (online-audio-converter.com).wav"))
            self.win_sound.setVolume(0.5)

            #Draw sound
            self.draw_sound = QSoundEffect()
            self.draw_sound.setSource(QUrl.fromLocalFile(r"c:\Users\85512\Downloads\game-over-38511 (online-audio-converter.com).wav"))
            self.draw_sound.setVolume(0.5)
        except Exception as e:
            QMessageBox.warning(self, "Sound Error", f"Could not load sound file: {e}")

    #UI
    def init_ui(self):
        layout = QVBoxLayout()
        # Title
        self.title_label = QLabel("Welcome to Tic-Tac-Toe 🎮")
        self.title_label.setFont(QFont("Arial", 20))
        self.title_label.setStyleSheet("color: white;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Option Label and Mode ComboBox
        option_layout = QHBoxLayout()
        self.option_label = QLabel("▶️Option")
        self.option_label.setFont(QFont("Times New Roman", 12))
        self.option_label.setStyleSheet("color: #90EE90;")
        option_layout.addWidget(self.option_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "🎮 Player vs AI (Random)",
            "🎯 Player vs AI (Center First)",
            "🧠 Player vs AI (Smart AI)",
            "👥 Player vs Player"
        ])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                font-size: 16px;
                padding: 5px;
                background-color: #444;
                color: white;
                border-radius: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: white;
                selection-background-color: #555;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        option_layout.addWidget(self.mode_combo)
        option_layout.addStretch() # Push combo box to the left
        layout.addLayout(option_layout)

        #Labels for win/draw results
        self.result_label_win = QLabel("")
        self.result_label_win.setFont(QFont("Arial", 18))
        self.result_label_win.setStyleSheet("color: #32CD32;")
        self.result_label_win.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label_win)

        self.result_label_draw = QLabel("")
        self.result_label_draw.setFont(QFont("Arial", 18))
        self.result_label_draw.setStyleSheet("color: #DC143C;")
        self.result_label_draw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label_draw)

        # Grid for game board
        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center the grid
        for i in range(3):
            for j in range(3):
                btn = QPushButton("")
                btn.setFixedSize(150, 130)
                btn.setFont(QFont("Arial", 24))
                btn.setStyleSheet("background-color: #2e2e3e; color: white; border-radius: 10px;")
                btn.clicked.connect(lambda _, x=i, y=j: self.player_move(x, y))
                self.grid.addWidget(btn, i, j)
                self.buttons[i][j] = btn
        layout.addLayout(self.grid)

        # Buttons for game actions
        button_row_layout = QHBoxLayout()
        self.reset_btn = QPushButton("🔄 Reset Game")
        self.reset_btn.setFont(QFont("Arial", 16))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e06c75;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d15c6a;
            }
            QPushButton:pressed {
                background-color: #c24d5b;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_game)
        button_row_layout.addWidget(self.reset_btn)
        

        #Button History
        self.history_btn = QPushButton("📜 Cases History")
        self.history_btn.setFont(QFont("Arial", 16))
        self.history_btn.setStyleSheet("""
            QPushButton {
                background-color: #98c379;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #89b46a;
            }
            QPushButton:pressed {
                background-color: #7aa55b;
            }
        """)
        self.history_btn.clicked.connect(self.show_history_window)
        button_row_layout.addWidget(self.history_btn)
        
        layout.addLayout(button_row_layout)

        self.setLayout(layout)

    def change_mode(self):
        """Handles game mode changes and resets the game."""
        text = self.mode_combo.currentText()
        if "Random" in text:
            self.mode = "Random AI"
        elif "Center" in text:
            self.mode = "Center AI"
        elif "Smart" in text:
            self.mode = "Smart AI"
        else:
            self.mode = "Player vs Player"
        self.reset_game()

    #Player X
    def player_move(self, i, j):
        """Handles a player's move."""
        if self.buttons[i][j].text() == "":
            self.buttons[i][j].setText(self.current_player)
            self.buttons[i][j].setFont(QFont("Arial Black", 40))
            
            # Record the move
            self._game_moves.append({'row': i, 'col': j, 'player': self.current_player})

            if self.current_player == "X":
                self.buttons[i][j].setStyleSheet("background-color: #2e2e3e; color: #00ffff; border-radius: 10px;")
            else:
                self.buttons[i][j].setStyleSheet("background-color: #2e2e3e; color: #ff5e78; border-radius: 10px;")

            winner = self.check_winner()
            self.show_result(winner)

            if not winner and not self.is_full():
                if self.mode == "Player vs Player":
                    self.current_player = "O" if self.current_player == "X" else "X"
                elif self.current_player == "X": # Only AI moves if current player is X (human)
                    QTimer.singleShot(500, self.ai_move)
    #Type of Ai
    def ai_move(self):
        """Handles the AI move depending on the selected difficulty."""
        if self.mode == "Player vs Player":
            return 
        i, j = -1, -1 

        #AI Random
        if self.mode == "Random AI":
            empty = [(r, c) for r in range(3) for c in range(3) if self.buttons[r][c].text() == ""]
            if empty:
                i, j = random.choice(empty)
        #AI Center
        elif self.mode == "Center AI":
            if self.buttons[1][1].text() == "":
                i, j = 1, 1
            else:
                empty = [(r, c) for r in range(3) for c in range(3) if self.buttons[r][c].text() == ""]
                if empty:
                    i, j = random.choice(empty)
        #AI Smart
        elif self.mode == "Smart AI":
            #Create a simplified board representation for minimax
            board_state = [[btn.text() for btn in row] for row in self.buttons]
            
            _, (move_i, move_j) = self._minimax_find_best_move(board_state, True)
            i, j = move_i, move_j
        
        if i != -1 and j != -1 and self.buttons[i][j].text() == "":
            self.buttons[i][j].setText("O")
            self.buttons[i][j].setStyleSheet("background-color: #2e2e3e; color: #ff5e78; border-radius: 10px;")
            self.buttons[i][j].setFont(QFont("Comic Sans MS", 40))
            
            #Record AI's move
            self._game_moves.append({'row': i, 'col': j, 'player': "O"})

            winner = self.check_winner()
            self.show_result(winner)

    #Implements the Minimax Algorithm:
    #This version operates on a board_state (list of lists of strings)
    def _minimax_find_best_move(self, board, is_maximizing_player):
        """
        Finds the best move using the Minimax algorithm.
        is_maximizing_player: True for AI ('O'), False for Player ('X')
        """
        winner = self._check_winner_board(board)
        if winner == "O":
            return 1, None
        elif winner == "X":
            return -1, None
        elif self._is_full_board(board):
            return 0, None

        if is_maximizing_player: # AI's turn ('O')
            best_score = -float('inf')
            best_move = None
            for r in range(3):
                for c in range(3):
                    if board[r][c] == "":
                        board[r][c] = "O"
                        score, _ = self._minimax_find_best_move(board, False)
                        board[r][c] = "" # Undo move
                        if score > best_score:
                            best_score = score
                            best_move = (r, c)
            return best_score, best_move
        else: #Player's turn ('X')
            best_score = float('inf')
            best_move = None
            for r in range(3):
                for c in range(3):
                    if board[r][c] == "":
                        board[r][c] = "X"
                        score, _ = self._minimax_find_best_move(board, True)
                        board[r][c] = "" # Undo move
                        if score < best_score:
                            best_score = score
                            best_move = (r, c)
            return best_score, best_move

    #Helperfunctions for minimax to operate on a board_state (list of lists)
    def _check_winner_board(self, board):
        """Checks for a winner on a given board state."""
        #Check rows
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != "":
                return board[i][0]
        #Check columns
        for i in range(3):
            if board[0][i] == board[1][i] == board[2][i] != "":
                return board[0][i]
        #Check diagonals
        if board[0][0] == board[1][1] == board[2][2] != "":
            return board[0][0]
        if board[0][2] == board[1][1] == board[2][0] != "":
            return board[0][2]
        return None

    def _is_full_board(self, board):
        """Checks if a given board state is full."""
        return all(board[i][j] != "" for i in range(3) for j in range(3))

    def check_winner(self):
        """Checks rows, columns, and diagonals for a winning line on the current game board."""
        for i in range(3):
            if self.buttons[i][0].text() == self.buttons[i][1].text() == self.buttons[i][2].text() != "":
                return self.buttons[i][0].text()
            if self.buttons[0][i].text() == self.buttons[1][i].text() == self.buttons[2][i].text() != "":
                return self.buttons[0][i].text()
        if self.buttons[0][0].text() == self.buttons[1][1].text() == self.buttons[2][2].text() != "":
            return self.buttons[0][0].text()
        if self.buttons[0][2].text() == self.buttons[1][1].text() == self.buttons[2][0].text() != "":
            return self.buttons[0][2].text()
        return None
    
    #Full Grid
    def is_full(self):
        """Checks if the board is completely filled (draw condition)."""
        return all(self.buttons[i][j].text() != "" for i in range(3) for j in range(3))
    
    #Show Result
    def show_result(self, winner):
        """Displays game results and prepares game history for saving."""
        game_ended = False
        if winner:
            self.result_label_win.setText(f"Player: {winner} Wins! 🎉")
            self.result_label_draw.setText("")
            self.disable_all()
            self.game_sound.stop() 
            self.win_sound.play()
            label = self.result_label_win
            game_ended = True
            final_winner = winner
        elif self.is_full():
            self.result_label_draw.setText("It's a Draw! 🤝")
            self.result_label_win.setText("")
            self.disable_all()
            self.game_sound.stop()
            self.draw_sound.play()
            label = self.result_label_draw
            game_ended = True
            final_winner = "Draw"
        else:
            return

        #Animate the result label
        animation = QPropertyAnimation(label, b"geometry")
        start_rect = label.geometry()
        jump_rect = QRect(start_rect.x(), start_rect.y() - 30, start_rect.width(), start_rect.height())
        animation.setDuration(300)
        animation.setStartValue(start_rect)
        animation.setKeyValueAt(0.5, jump_rect)
        animation.setEndValue(start_rect)
        animation.start()
        self._result_animation = animation # Keep a reference to prevent garbage collection

        if game_ended:
            self.prepare_game_history(final_winner)

    def prepare_game_history(self, winner):
        """Collects game data and stores it in last_game_data for later saving."""
        self.last_game_data = {
            "mode": self.mode,
            "winner": winner,
            "move_history": list(self._game_moves), #Create a copy
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def disable_all(self):
        """Disables all buttons on the board after the game ends."""
        for row in self.buttons:
            for btn in row:
                btn.setEnabled(False)

    def reset_game(self):
        """Resets the game board and state."""
        self.game_sound.play()
        self.result_label_win.setText("")
        self.result_label_draw.setText("")
        self.current_player = "X"
        self._game_moves = [] #Clear move history for new game
        self.last_game_data = None #Clear last game data

        for i in range(3):
            for j in range(3):
                btn = self.buttons[i][j]
                btn.setText("")
                btn.setEnabled(True)
                btn.setStyleSheet("background-color: #2e2e3e; color: white; border-radius: 10px;")
        
    def show_history_window(self):
        """Opens the HistoryWindow to display game history."""
        #HistoryWindow now handles its own database connection via GameHistoryDB
        history_dialog = HistoryWindow(self) 
        history_dialog.exec() #Use exec() for modal dialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(r".venv_TTT_Game_AI/Image/icons8-tic-tac-toe-53.png"))
    game = TicTacToeGame()
    game.show()
    sys.exit(app.exec())

    