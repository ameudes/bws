import streamlit as st
import pandas as pd
import json
import os
import itertools
import random
import time 
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.oauth2 import service_account


#Principale modifs :  Génération aléatoire constante des séquences d'option pour chaque participants, choix de la séquence à appliquer et mise à jour du json dès le début, Mise à jour du json à la fin après soumission
#Ajout des éléments dans un session_state pour éviter un rerun à chaque selection du st.radio qui modifie tout.
#Ajout de l'envoi vers google sheet
#Prise en compte de st.secret
#Ajout du requirement avec pipreqs --use-local --force
#Ajout des labels de chaque choix
#Modification du welcome page

#Quelques fonctions clés
def read_subsetgroup(): # Fonction pour lire les indices depuis le fichier JSON
    if os.path.exists("subsetgroup.json"):
        with open("subsetgroup.json", "r") as f:
            data = json.load(f)
            return data.get("remaining")

def update_subsetgroup(indice): #Fonction pour retirer un indice du remaining
    with open("subsetgroup.json","r") as f:
        data = json.load(f)
        data["remaining"].remove(indice)    
    with open("subsetgroup.json", "w") as o:
        json.dump(data, o)
                
def write_subsetgroup(indice): # Fonction pour écrire les indices terminés dans le fichier JSON
    with open("subsetgroup.json","r") as f:
        data = json.load(f)
        data["end"].append(indice)
      
    with open("subsetgroup.json", "w") as o:
        json.dump(data, o)


#Stockage de la liste de question spécifique au user dans un session_state
if 'list_user' not in st.session_state:
    
    #remaining = read_subsetgroup() # Modif pretest :  pas besoin de charger le remaining
    selected = 1  # Modif pretest : Tout le monde voit le questionnaire 1 : Choix du premier indice de la liste
    #update_subsetgroup(selected)  # Modif pretest : Pas besoin de mettre à jour le remaining :  Mise à jour du fichier : suppression de cet indice de remaining
        
    #Lecture du fichier contenant les listes des séquence d'options (lists.json)
    with open("lists.json", "r") as f:
            liste = json.load(f)
            st.session_state.lists = liste[selected] #Stocker dans la session la séquence de questions (options) associée à l'indice sélectionné
            st.session_state.selected=selected #Stocker dans la session l'indice retenu pour le user
    
    #Lecture du fichier contenant la liste des labels
    with open ("labels.json", "r") as l:
        lab= json.load(l)
        st.session_state.labels = lab[selected]
        
        
    st.session_state.list_user = True


# Utilisation de la séquence sélectionnée pour les choices
lists = st.session_state.lists
# Utilisation de la séquence sélectionnée pour les labels
labels=st.session_state.labels




#Multipage survey begin
# Initialize session state variables if they don't exist
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

if 'responses' not in st.session_state:
    st.session_state.responses = []

#Welcome page to introduce participants
if 'start' not in st.session_state:
    st.session_state.start = False


##### Default / Welcome Page 
if not st.session_state.start:
    st.title("Bienvenue")
    st.write("""
        Ce questionnaire explore l'importance de divers aspects des données ouvertes (open data) dans un contexte de participation citoyenne.  
        
        **La participation citoyenne** désigne l'engagement des citoyens dans les processus décisionnels publics.  
        
        **Les données ouvertes** permettent d'accéder librement à des informations publiques essentielles pour renforcer la transparence et l'implication citoyenne.  

        Dans ce questionnaire, vous êtes invités à choisir, pour chaque groupe de caractéristiques, l’aspect le plus important et celui le moins important dans le cadre d'une participation citoyenne.  
        
        **Durée estimée** : 7 minutes
    """)
    if st.button("Débuter"):
        st.session_state.start = True
        st.experimental_rerun()

else : 


    ####### Actual SURVEY
    # Check if we have completed all lists
    if st.session_state.current_index >= len(lists):
        st.title("Merci de votre participation !")
        
        with st.spinner("Envoi des données... Veuillez patienter quelques secondes"):
            time.sleep(3)  
        st.success("Données envoyées!")
        
        #Send the data to Google sheet
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        #credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes) #Méthode brute abandonnée pour utiliser st.secrets afin de préserver les credentials
        creds_info = json.loads(st.secrets["credentials"])
        credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key('1c6kscX0AT_IRS3zSsiAzg0Kg6WiajFBhr2YwAUayVeI')  #Access the Fille
        df = pd.DataFrame(st.session_state.responses)
        data_values = df.values.tolist()
        gs.values_append('data', {'valueInputOption': 'RAW'}, {'values': data_values})      
        
        
        #write_subsetgroup(st.session_state.selected) # Add the selected indice to end in subsetgroup.json
        
        st.write("Vos réponses ont été enregistrées")

    else:
        st.title(f"Set {st.session_state.current_index + 1} sur {len(lists)}")
        
        # Get the current list of options
        data = lists[st.session_state.current_index]
        
        #Get the current list of labels
        choices=labels[st.session_state.current_index]

        
        
    #######Here we put the code for a single page survey     

        # --- Custom CSS for table styling ---
        # This CSS defines classes for table headers and cells with visible borders.
        st.markdown(
            """
            <style>
            /* Table header style */
            .table-header {
                font-weight: bold;
                background-color: #f1f1f1;
                border: 1px solid black;
                padding: 10px;
                text-align: center;
            }
            /* Table cell style */
            .table-cell {
                border: 1px solid black;
                padding: 10px;
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # --- App Title ---
        #st.title("")
        st.markdown("Mentionner dans un contexte de participation citoyenne :<br>🟩 l’aspect que vous trouvez le plus important,<br>🟥 celui que vous jugez le moins important.", unsafe_allow_html=True)



        # --- Create the table header row using st.columns ---
        #header_cols = st.columns([1.1, 2.8, 1.1])
        #with header_cols[0]:
        #    st.markdown("<div class='table-header' style='color: red;'>Moins important</div>", unsafe_allow_html=True)
        #with header_cols[1]:
        #    st.markdown("<div class='table-header'>Dimension</div>", unsafe_allow_html=True)
        #with header_cols[2]:
        #    st.markdown("<div class='table-header' style='color: green;'>Plus important</div>", unsafe_allow_html=True)

        # --- List to store responses for each row # We replace choices by the current list of labels at line 140
        #choices=[1,2,3]

        cols = st.columns([1.1, 2.8, 1.1])

        #First, here we add both default key (default=0) to st.radio associated to most_choice and least_choice, in order to force equality and have a checking on whether the same dimension is selected as most and least important 
        #Here to avoid the fact that the previous state choices are still chown in the current state, we add the current session index to every st.radio key for most important and least important
        #Now responsive part we redesign the tables, we no more use the table header style 
        #We add a welcome page


        # In the right cell, we put a Streamlit radio widget for "Most Important" selection.
        with cols[2]:
            # Wrap the radio widget in a div that is styled to align its content at the top.
            
            
            st.markdown(
                """
                <div style="display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
                    <style>
                        .stRadio [role="radiogroup"] {
                            align-items: left;
                        }
                    </style>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div style='color: green; text-align: left;'><strong>Plus important</strong></div>", unsafe_allow_html=True)
            most_choice = st.radio(" ", options=choices, key=f"most_{st.session_state.current_index}", index=0)
            st.markdown("</div>", unsafe_allow_html=True)
            
        # In the left cell we do the same 
        with cols[0]:
            # Wrap the radio widget in a div that is styled to align its content at the top.
            st.markdown(
                """
                <div style="display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
                    <style>
                        .stRadio [role="radiogroup"] {
                            align-items: left;
                        }
                    </style>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<div style='color: red; text-align: left;'><strong>Moins important</strong></div>", unsafe_allow_html=True)
            least_choice = st.radio(" ", options=choices, key=f"least_{st.session_state.current_index}",index=0)
            st.markdown("</div>", unsafe_allow_html=True)    
                    
        # --- Create one table row for each survey question ---
        for i,row in enumerate(data):       
            # In the center cell, display the list of options
            with cols[1]:
                # Create a numbered list with the row number using the 'start' attribute
                cell_text = "".join([f"<li> <strong>{choices[i]}</strong>: {row}</li>"])  # on rajoute le label dans le display de l'option' 
                st.markdown(
                    f"<div class='table-cell' style='text-align: left;'><ol start='{i+1}'>{cell_text}</ol></div>",
                    unsafe_allow_html=True)  
                        
    #######End of the single page survey code 
        
        
        
             
        # Button to submit the current response and move to the next list
        if st.button("Suivant", key=f"next"):
            if most_choice==least_choice:
                st.error('Le moins important et le plus important doivent êtres différents', icon="🚨") 
            else:    
            # Save the current response (list number and selected option)
                st.session_state.responses.append({
                    "Participant": st.session_state.selected,
                    "Subset": st.session_state.current_index + 1,
                    "Most Important": most_choice,
                    "Least Important": least_choice
                })
                # Move to the next list
                st.session_state.current_index += 1
                
                # Rerun the app so that the new task appears
                st.experimental_rerun()

    #progression bar            
    st.progress(int((st.session_state.current_index/len(lists))*100))