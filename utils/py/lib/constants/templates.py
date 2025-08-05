#!/usr/bin/env python3
"""
API Example Templates

Template definitions for generating API examples for different method categories.
Templates provide structured patterns for creating comprehensive test cases.
"""

from typing import Dict, Any


class ExampleTemplates:
    """
    Container for API example generation templates.
    
    Templates are organized by method category and provide base patterns
    for generating comprehensive test cases across all API methods.
    """
    
    @staticmethod
    def get_activation_templates() -> Dict[str, Dict[str, Any]]:
        """Get templates for coin/token activation methods."""
        return {
            'basic_activation': {
                'description': 'Basic activation with minimal parameters',
                'params': {
                    'coin': 'DOC',
                    'activation_params': {
                        'mode': {
                            'rpc': 'https://rick.kmd.earth',
                            'validate_every_nth_block': 10
                        }
                    }
                }
            },
            'with_custom_confirmations': {
                'description': 'Activation with custom confirmation requirements',
                'params': {
                    'coin': 'MARTY',
                    'activation_params': {
                        'mode': {
                            'rpc': 'https://morty.kmd.earth',
                            'validate_every_nth_block': 5
                        },
                        'required_confirmations': 3
                    }
                }
            },
            'electrum_mode': {
                'description': 'Activation using Electrum servers',
                'params': {
                    'coin': 'LTC',
                    'activation_params': {
                        'mode': {
                            'electrum': {
                                'servers': [
                                    {'url': 'electrum1.cipig.net:10063'},
                                    {'url': 'electrum2.cipig.net:10063'}
                                ]
                            }
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_task_operation_templates() -> Dict[str, Dict[str, Any]]:
        """Get templates for task-based operations (init, status, cancel, user_action)."""
        return {
            'init_task': {
                'description': 'Initialize a new task',
                'applies_to_operations': ['init'],
                'params': {
                    'activation_params': {
                        'mode': {
                            'rpc': 'https://example.com',
                            'validate_every_nth_block': 10
                        }
                    }
                }
            },
            'status_check': {
                'description': 'Check task status',
                'applies_to_operations': ['status'],
                'params': {
                    'task_id': 1234567890
                }
            },
            'cancel_task': {
                'description': 'Cancel running task',
                'applies_to_operations': ['cancel'],
                'params': {
                    'task_id': 1234567890
                }
            },
            'user_action_confirm': {
                'description': 'Confirm user action for task',
                'applies_to_operations': ['user_action'],
                'params': {
                    'task_id': 1234567890,
                    'user_action': {
                        'action_type': 'confirm',
                        'confirmation': True
                    }
                }
            }
        }
    
    @staticmethod
    def get_trading_templates() -> Dict[str, Dict[str, Any]]:
        """Get templates for trading and order-related methods."""
        return {
            'basic_order': {
                'description': 'Basic trading order',
                'params': {
                    'base': 'DOC',
                    'rel': 'MARTY',
                    'price': '1.0',
                    'volume': '10.0'
                }
            },
            'advanced_order': {
                'description': 'Advanced order with custom parameters',
                'params': {
                    'base': 'KMD',
                    'rel': 'BTC',
                    'price': '0.00001',
                    'volume': '100.0',
                    'order_type': {
                        'type': 'GoodTillCancelled'
                    }
                }
            },
            'market_maker': {
                'description': 'Market maker configuration',
                'params': {
                    'pairs': [
                        {'base': 'DOC', 'rel': 'MARTY'},
                        {'base': 'KMD', 'rel': 'BTC'}
                    ],
                    'spreads': {
                        'DOC/MARTY': '0.02',
                        'KMD/BTC': '0.01'
                    }
                }
            }
        }
    
    @staticmethod
    def get_wallet_templates() -> Dict[str, Dict[str, Any]]:
        """Get templates for wallet management methods."""
        return {
            'basic_balance': {
                'description': 'Check coin balance',
                'params': {
                    'coin': 'KMD'
                }
            },
            'withdrawal': {
                'description': 'Withdraw funds',
                'params': {
                    'coin': 'KMD',
                    'to': 'RXL3YXG2ceaB6C5hfJcN4fvmHH2JFuwduh',
                    'amount': '10.0'
                }
            },
            'max_withdrawal': {
                'description': 'Maximum withdrawal amount',
                'params': {
                    'coin': 'KMD',
                    'to': 'RXL3YXG2ceaB6C5hfJcN4fvmHH2JFuwduh',
                    'max': True
                }
            }
        }
    
    @staticmethod
    def get_utility_templates() -> Dict[str, Dict[str, Any]]:
        """Get templates for utility and information methods."""
        return {
            'version_check': {
                'description': 'Check API version',
                'params': {}
            },
            'address_validation': {
                'description': 'Validate address format',
                'params': {
                    'coin': 'KMD',
                    'address': 'RXL3YXG2ceaB6C5hfJcN4fvmHH2JFuwduh'
                }
            },
            'address_conversion': {
                'description': 'Convert address format',
                'params': {
                    'coin': 'KMD',
                    'from': 'RXL3YXG2ceaB6C5hfJcN4fvmHH2JFuwduh',
                    'to_address_format': {
                        'format': 'segwit'
                    }
                }
            }
        }
    
    @staticmethod
    def get_all_templates() -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get all templates organized by category."""
        return {
            'activation': ExampleTemplates.get_activation_templates(),
            'task_operation': ExampleTemplates.get_task_operation_templates(),
            'trading': ExampleTemplates.get_trading_templates(),
            'wallet': ExampleTemplates.get_wallet_templates(),
            'utility': ExampleTemplates.get_utility_templates()
        }
    
    @staticmethod
    def get_templates_for_category(category: str) -> Dict[str, Dict[str, Any]]:
        """Get templates for a specific category."""
        all_templates = ExampleTemplates.get_all_templates()
        return all_templates.get(category, {}) 