#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Question:
    id: int
    text: str
    options: List[str]
    correct_indices: List[int]


class QuestionParser:
    """Parser pytań z pliku pyta_updated.dat"""
    
    @staticmethod
    def parse_questions(filepath: Path) -> Dict[int, Question]:
        """Parsuje pytania z pliku DAT"""
        questions = {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(' ', 1)
                if len(parts) < 2:
                    continue
                
                try:
                    q_id = int(parts[0])
                except ValueError:
                    continue
                
                text_and_options = parts[1]
                # Rozdzielanie pytania od odpowiedzi
                segments = text_and_options.split('*')
                
                if len(segments) < 2:
                    continue
                
                question_text = segments[0]
                options = []
                correct_indices = []
                
                for idx, seg in enumerate(segments[1:]):
                    if seg.startswith('[X]'):
                        options.append(seg[3:])
                        correct_indices.append(len(options) - 1)
                    else:
                        options.append(seg)
                
                if options:
                    questions[q_id] = Question(
                        id=q_id,
                        text=question_text,
                        options=options,
                        correct_indices=correct_indices
                    )
        
        return questions


class ModuleLoader:
    """Loader modułów z JSON"""
    
    @staticmethod
    def load_modules(filepath: Path) -> Dict[int, Dict]:
        """Wczytuje moduły z pliku JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modules = {}
        for module in data['modules']:
            modules[module['id']] = {
                'name': module['name'],
                'description': module['description'],
                'questions': module['questions']
            }
        return modules


class Quiz:
    """Aplikacja do nauki pytań"""
    
    def __init__(self, questions: Dict[int, Question], modules: Dict[int, Dict]):
        self.questions = questions
        self.modules = modules
        self.current_index = 0
        self.quiz_questions = []
        self.stats = {'correct': 0, 'wrong': 0, 'total': 0}
    
    def select_mode(self) -> Tuple[List[int], str] | None:
        """Pozwala wybrać tryb: losowe pytania czy z modułu"""
        self.clear_screen()
        print("=" * 60)
        print("QUIZ - SYSTEM NAUKI PYTAŃ EGZAMINACYJNYCH")
        print("=" * 60)
        print()
        
        options = [
            "1. Losowe pytania (wszystkie)",
            "2. Pytania z wybranego modułu",
            "3. Wyjście"
        ]
        
        selected = 0
        while True:
            self.clear_screen()
            print("=" * 60)
            print("WYBIERZ TRYB NAUKI")
            print("=" * 60)
            print()
            
            for idx, opt in enumerate(options):
                marker = "→ " if idx == selected else "  "
                print(f"{marker}{opt}")
            
            print()
            print("Użyj strzałek ↑↓ lub jk, Enter aby wybrać, ESC aby wyjść")
            
            key = self.get_arrow_key()
            
            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == 'enter':
                break
            elif key == 'esc':
                return None
        
        if selected == 0:
            q_ids = list(self.questions.keys())
            mode = "Losowe pytania"
        elif selected == 1:
            module_id = self.select_module()
            if module_id is None:
                return self.select_mode()
            q_ids = self.modules[module_id]['questions']
            mode = f"Moduł: {self.modules[module_id]['name']}"
        else:  # selected == 2
            return None
        
        return q_ids, mode
    
    def select_module(self) -> int | None:
        """Pozwala wybrać moduł"""
        module_list = sorted(self.modules.keys())
        selected = 0
        
        while True:
            self.clear_screen()
            print("=" * 60)
            print("WYBIERZ MODUŁ")
            print("=" * 60)
            print()
            
            for idx, m_id in enumerate(module_list):
                marker = "→ " if idx == selected else "  "
                name = self.modules[m_id]['name']
                count = len(self.modules[m_id]['questions'])
                print(f"{marker}[{m_id}] {name} ({count} pytań)")
            
            print()
            print("Użyj strzałek ↑↓ lub jk, Enter aby wybrać, ESC aby wróć")
            
            key = self.get_arrow_key()
            
            if key == 'up':
                selected = (selected - 1) % len(module_list)
            elif key == 'down':
                selected = (selected + 1) % len(module_list)
            elif key == 'enter':
                return module_list[selected]
            elif key == 'esc':
                return None
    
    def run_quiz(self, question_ids: List[int]):
        """Uruchamia quiz"""
        self.quiz_questions = random.sample(question_ids, min(len(question_ids), len(question_ids)))
        self.current_index = 0
        self.stats = {'correct': 0, 'wrong': 0, 'total': len(self.quiz_questions)}
        
        while self.current_index < len(self.quiz_questions):
            q_id = self.quiz_questions[self.current_index]
            
            if q_id not in self.questions:
                self.current_index += 1
                continue
            
            question = self.questions[q_id]
            user_answers = self.show_question(question, self.current_index + 1)
            
            if user_answers is None:  # Wciśnięto ESC
                self.show_exit_confirmation()
                break
            
            is_correct = self.check_answers(user_answers, question.correct_indices)
            self.show_result(is_correct, question, user_answers)
            
            if is_correct:
                self.stats['correct'] += 1
            else:
                self.stats['wrong'] += 1
            
            self.current_index += 1
        
        self.show_summary()
    
    def show_question(self, question: Question, number: int) -> List[int] | None:
        """Wyświetla pytanie i pozwala wybrać odpowiedzi (może być wiele)"""
        selected = 0
        checked = set()
        
        while True:
            self.clear_screen()
            print("=" * 60)
            print(f"PYTANIE {number}/{len(self.quiz_questions)}")
            print("=" * 60)
            print()
            print(f"ID: {question.id}")
            print()
            print(f"Treść: {question.text}")
            print()
            print("Odpowiedzi:")
            print()
            
            for idx, option in enumerate(question.options):
                is_selected = idx == selected
                is_checked = idx in checked
                
                marker = "→" if is_selected else " "
                checkbox = "[x]" if is_checked else "[ ]"
                
                print(f" {marker} {checkbox} [{idx + 1}] {option}")
            
            print()
            print("Użyj strzałek ↑↓ lub jk, SPACE aby zaznaczyć, Enter aby potwierdzić, ESC aby wyjść")
            
            key = self.get_arrow_key()
            
            if key == 'up':
                selected = (selected - 1) % len(question.options)
            elif key == 'down':
                selected = (selected + 1) % len(question.options)
            elif key == 'space':
                if selected in checked:
                    checked.remove(selected)
                else:
                    checked.add(selected)
            elif key == 'enter':
                if checked:
                    return list(checked)
            elif key == 'esc':
                return None
    
    def show_result(self, is_correct: bool, question: Question, user_answers: List[int] = None):
        """Wyświetla wynik odpowiedzi"""
        self.clear_screen()
        print("=" * 60)
        
        if is_correct:
            print("✓ POPRAWNA ODPOWIEDŹ!")
            print("=" * 60)
        else:
            print("✗ BŁĘDNA ODPOWIEDŹ")
            print("=" * 60)
        
        print()
        print(f"ID: {question.id}")
        print()
        print(f"Treść pytania: {question.text}")
        print()
        print("Odpowiedzi:")
        
        for idx, option in enumerate(question.options):
            is_correct_answer = idx in question.correct_indices
            was_selected = user_answers and idx in user_answers
            
            if is_correct_answer and was_selected:
                marker = "✓✓"
            elif is_correct_answer:
                marker = "✓ "
            elif was_selected:
                marker = "✗ "
            else:
                marker = "  "
            
            print(f"  {marker} [{idx + 1}] {option}")
        
        print()
        print("Naciśnij Enter aby kontynuować...")
        self.wait_for_enter()
    
    def check_answers(self, user_answers: List[int], correct_indices: List[int]) -> bool:
        """Sprawdza czy odpowiedzi są poprawne"""
        return set(user_answers) == set(correct_indices)
    
    def show_summary(self):
        """Wyświetla podsumowanie quizu"""
        self.clear_screen()
        print("=" * 60)
        print("PODSUMOWANIE")
        print("=" * 60)
        print()
        print(f"Łącznie pytań: {self.stats['total']}")
        print(f"Poprawne: {self.stats['correct']} ({int(self.stats['correct']/self.stats['total']*100) if self.stats['total'] > 0 else 0}%)")
        print(f"Błędne: {self.stats['wrong']} ({int(self.stats['wrong']/self.stats['total']*100) if self.stats['total'] > 0 else 0}%)")
        print()
        
        if self.stats['correct'] / self.stats['total'] >= 0.8:
            print("Doskonale! 🎉")
        elif self.stats['correct'] / self.stats['total'] >= 0.6:
            print("Dobrze! 👍")
        else:
            print("Warto ćwiczyć! 📚")
        
        print()
        print("Naciśnij Enter aby wróć do menu...")
        self.wait_for_enter()
    
    def show_exit_confirmation(self):
        """Potwierdza wyjście"""
        self.clear_screen()
        print("=" * 60)
        print("OPUSZCZANIE QUIZU")
        print("=" * 60)
        print()
        print(f"Odpowiedziałeś na {self.current_index} z {len(self.quiz_questions)} pytań")
        print(f"Poprawne: {self.stats['correct']}")
        print(f"Błędne: {self.stats['wrong']}")
        print()
        print("Naciśnij Enter aby wrócić do menu...")
        self.wait_for_enter()
    
    @staticmethod
    def clear_screen():
        """Czyści ekran"""
        import os
        os.system('cls' if sys.platform == 'win32' else 'clear')
    
    @staticmethod
    def get_arrow_key() -> str:
        """Pobiera klawisz (strzałki, Enter, ESC, Space)"""
        if sys.platform == 'win32':
            import msvcrt
            key = msvcrt.getch()
            if key == b'\xe0':
                key2 = msvcrt.getch()
                if key2 == b'H':
                    return 'up'
                elif key2 == b'P':
                    return 'down'
            elif key == b'\r':
                return 'enter'
            elif key == b'\x1b':
                return 'esc'
            elif key == b' ':
                return 'space'
            elif key == b'j':
                return 'down'
            elif key == b'k':
                return 'up'
        else:
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                key = sys.stdin.read(1)
                
                if key == '\x1b':
                    next1 = sys.stdin.read(1)
                    if next1 == '[':
                        next2 = sys.stdin.read(1)
                        if next2 == 'A':
                            return 'up'
                        elif next2 == 'B':
                            return 'down'
                    return 'esc'
                elif key == '\r':
                    return 'enter'
                elif key == ' ':
                    return 'space'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        return ''
    
    @staticmethod
    def wait_for_enter():
        """Czeka na Enter"""
        if sys.platform == 'win32':
            import msvcrt
            while True:
                key = msvcrt.getch()
                if key == b'\r':
                    break
        else:
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    key = sys.stdin.read(1)
                    if key == '\r':
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main():
    """Główna funkcja"""
    base_dir = Path(__file__).parent
    
    # Wczytanie danych
    print("Wczytywanie pytań...")
    questions = QuestionParser.parse_questions(base_dir / 'pyta_updated.dat')
    print(f"Wczytano {len(questions)} pytań")
    
    print("Wczytywanie modułów...")
    modules = ModuleLoader.load_modules(base_dir / 'moduly.json')
    print(f"Wczytano {len(modules)} modułów")
    
    print()
    input("Naciśnij Enter aby kontynuować...")
    
    # Uruchomienie aplikacji
    quiz = Quiz(questions, modules)
    
    while True:
        result = quiz.select_mode()
        
        if result is None:
            break
        
        question_ids, mode = result
        
        if not question_ids:
            Quiz.clear_screen()
            print("Brak pytań do nauki!")
            continue
        
        quiz.quiz_questions = random.sample(question_ids, min(20, len(question_ids)))
        quiz.run_quiz(question_ids)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWyjście z aplikacji.")
        sys.exit(0)
    except Exception as e:
        print(f"\nBłąd: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
