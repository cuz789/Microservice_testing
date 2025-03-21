"""
This module defines the routes for user-related operations in a Flask application using Flask-RESTx.
It includes endpoints for creating and updating user information, with validation and error handling.
Classes:
    UserList(Resource): Handles the creation of new users.
    User(Resource): Handles the updating of existing users.
Routes:
    /users/ (POST): Creates a new user.
    /users/<string:id> (PUT): Updates an existing user.
Functions:
    UserList.post(): Creates a new user with the provided data.
    User.put(id: str): Updates an existing user with the provided data.
"""

from flask import request, Flask, current_app
from flask_restx import Namespace, Resource, fields
from bson.objectid import ObjectId
import uuid
from user_service_v1.app.models import api, user_model, delivery_address_model
from user_service_v1.app.events import publish_user_update_event

# The current_app variable is a proxy to the Flask application handling the request.
current_app : Flask

service_version = 'v1'
print(f"Using User Service: {service_version}")

@api.route('/')
class UserList(Resource):
    @api.expect(user_model)
    @api.marshal_with(user_model, code=201)
    def post(self) -> tuple:
        """
        Handles the HTTP POST request to create a new user.
        This method performs the following steps:
        1. Parses the JSON data from the request.
        2. Validates the presence and format of required fields.
        3. Ensures no additional fields are present in the request.
        4. Validates the structure of the 'deliveryAddress' field.
        5. Checks if any of the provided email addresses already exist in the database.
        6. Generates a unique userId for the new user.
        7. Inserts the new user data into the database.
        8. Retrieves and returns the newly created user.
        Returns:
            tuple: A tuple containing the newly created user data and the HTTP status code 201.
        Raises:
            werkzeug.exceptions.HTTPException: If the JSON data is invalid, required fields are missing,
                               additional fields are present, or email addresses already exist.
        """

        try:
            data: dict = request.json
        except Exception as e:
            api.abort(400, f'Invalid JSON data: {str(e)}')
        
        # Ensure no other fields are present
        allowed_fields = {'emails', 'deliveryAddress', 'firstName', 'lastName', 'phoneNumber', 'createdAt', 'updatedAt'}
        for field in data:
            if field not in allowed_fields:
                api.abort(400, f'Invalid field: {field}')
        
        if 'emails' not in data or not data['emails']:
            api.abort(400, 'emails is a required field')
        if 'deliveryAddress' not in data:
            api.abort(400, 'deliveryAddress is a required field')
        
                # Validate deliveryAddress
        if 'deliveryAddress' in data:
            delivery_address = data['deliveryAddress']
            required_fields = ['street', 'city', 'state', 'postalCode', 'country']
            if not isinstance(delivery_address, dict):
                api.abort(400, 'deliveryAddress must be an object')
            for field in required_fields:
                if field not in delivery_address or not isinstance(delivery_address[field], str):
                    api.abort(400, f'deliveryAddress must contain a valid {field}')
                    
        users_collection = current_app.users_collection
        # Check if any of the emails already exist in the database
        existing_user = users_collection.find_one({'emails': {'$in': data['emails']}})
        if existing_user:
            api.abort(400, 'One or more email addresses are already in use')
            
        # Generate a unique userId
        data['userId'] = str(uuid.uuid4())
        user_id: ObjectId = users_collection.insert_one(data).inserted_id
        user: dict = users_collection.find_one({'_id': ObjectId(user_id)})
        return user, 201
    
    
@api.route('/<string:id>')
@api.response(404, 'User not found')
class User(Resource):
    @api.expect(user_model)
    @api.marshal_with(user_model)
    def put(self, id: str) -> dict:
        """
        Update user information based on the provided user ID.
        Args:
            id (str): The unique identifier of the user.
        Returns:
            dict: A list containing the old user data and the updated user data.
        Raises:
            HTTPException: If the JSON data is invalid.
            HTTPException: If any field other than 'emails' or 'deliveryAddress' is present.
            HTTPException: If neither 'emails' nor 'deliveryAddress' is provided.
            HTTPException: If 'emails' is not a list of valid email addresses.
            HTTPException: If 'deliveryAddress' is not a valid object with required fields.
            HTTPException: If the user with the given ID is not found.
        """

        try:
            data: dict = request.json
        except Exception as e:
            api.abort(400, f'Invalid JSON data: {str(e)}')
        
        # Ensure no other fields are present
        allowed_fields = {'emails', 'deliveryAddress'}
        for field in data:
            if field not in allowed_fields:
                api.abort(400, f'Invalid field: {field}')
                
        if 'emails' not in data and 'deliveryAddress' not in data:
            api.abort(400, 'Either emails or deliveryAddress is required')
        
        # Validate emails
        if 'emails' in data:
            if not isinstance(data['emails'], list) or not all(isinstance(email, str) and '@' in email for email in data['emails']):
                api.abort(400, 'emails must be an array of valid email addresses')

        # Validate deliveryAddress
        if 'deliveryAddress' in data:
            delivery_address = data['deliveryAddress']
            required_fields = ['street', 'city', 'state', 'postalCode', 'country']
            if not isinstance(delivery_address, dict):
                api.abort(400, 'deliveryAddress must be an object')
            for field in required_fields:
                if field not in delivery_address or not isinstance(delivery_address[field], str):
                    api.abort(400, f'deliveryAddress must contain a valid {field}')
        
        users_collection = current_app.users_collection
        old_user = users_collection.find_one({'userId': id})
        if not old_user:
            api.abort(404, "User not found")

        users_collection.update_one({'userId': id}, {'$set': data})
        new_user: dict = users_collection.find_one({'userId': id})
        
        emails = new_user["emails"]
        deliveryAddress = new_user["deliveryAddress"]

        # Publish the update event
        publish_user_update_event(id, emails, deliveryAddress)
        return [old_user, new_user]
    
    @api.marshal_with(user_model)
    def get(self, id: str) -> dict:
        """
        Retrieves a user based on the provided user ID.
        Args:
            id (str): The unique identifier of the user.
        Returns:
            dict: The user data.
        Raises:
            HTTPException: If the user with the given ID is not found.
        """
        users_collection = current_app.users_collection
        user = users_collection.find_one({'userId': id})
        if not user:
            api.abort(404, "User not found")
        return user
