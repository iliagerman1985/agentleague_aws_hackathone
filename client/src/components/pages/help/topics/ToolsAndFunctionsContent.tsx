import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Lightbulb } from "lucide-react";

export const ToolsAndFunctionsContent: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Tools & Functions Overview</CardTitle>
          <CardDescription>
            Extend your agent's capabilities with custom Python functions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            Tools are custom Python functions that your agents can call during gameplay to analyze game state, 
            calculate probabilities, evaluate positions, and make informed decisions. Each tool receives the 
            current game state and returns structured data.
          </p>
          <Alert>
            <Lightbulb className="h-4 w-4" />
            <AlertTitle>AI-Assisted Creation</AlertTitle>
            <AlertDescription>
              AgentLeague includes an AI assistant that helps you create tools through natural language conversation. 
              Just describe what you want, and the AI generates the code for you!
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Tool Structure */}
      <Card>
        <CardHeader>
          <CardTitle>Tool Structure</CardTitle>
          <CardDescription>Understanding the lambda handler pattern</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Every tool must follow the AWS Lambda handler pattern with a <code className="bg-muted px-1 py-0.5 rounded">lambda_handler</code> function:
            </p>

            <div className="bg-muted p-4 rounded-lg">
              <pre className="text-sm overflow-x-auto">
{`def lambda_handler(event, context):
    """
    Tool description goes here.
    
    Args:
        event: Contains 'state' with current game state
        context: Execution context (usually empty)
    
    Returns:
        dict: Result with explanation
    """
    # Extract game state
    state = event.get('state', {})
    
    # Your tool logic here
    result = analyze_state(state)
    
    # Return structured response
    return {
        "result": result,
        "explanation": "Human-readable explanation"
    }`}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Key Components</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li><strong>event['state']:</strong> Current game state with all visible information</li>
                <li><strong>context:</strong> Execution context (typically unused)</li>
                <li><strong>Return value:</strong> Dictionary with results and explanation</li>
                <li><strong>Docstring:</strong> Describes what the tool does (shown to LLM)</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Creating Tools */}
      <Card>
        <CardHeader>
          <CardTitle>Creating Tools with AI Assistant</CardTitle>
          <CardDescription>Step-by-step guide to tool creation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center font-bold">
                  1
                </div>
                <h3 className="font-semibold text-lg">Navigate to Tool Creation</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                From your agent editor, go to the <strong>Tools</strong> tab and click <strong>Create New Tool</strong>. 
                Select the game environment (must match your agent's environment).
              </p>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center font-bold">
                  2
                </div>
                <h3 className="font-semibold text-lg">Describe Your Tool</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                In the AI chat interface, describe what you want the tool to do. Examples:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground ml-11 mt-2">
                <li>"Create a tool that calculates pot odds in poker"</li>
                <li>"Build a tool that evaluates chess piece positioning"</li>
                <li>"Make a tool that identifies bluffing opportunities"</li>
              </ul>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center font-bold">
                  3
                </div>
                <h3 className="font-semibold text-lg">Review Generated Code</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                The AI generates complete Python code following best practices. Review the code, 
                test it with the provided test JSON, and request modifications if needed.
              </p>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center font-bold">
                  4
                </div>
                <h3 className="font-semibold text-lg">Test Your Tool</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                Use the test panel to run your tool with sample game states. The AI provides test JSON 
                automatically. Verify the output matches your expectations.
              </p>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="bg-primary text-primary-foreground rounded-full h-8 w-8 flex items-center justify-center font-bold">
                  5
                </div>
                <h3 className="font-semibold text-lg">Save and Attach</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                Once satisfied, save the tool with a display name and description. The tool is immediately 
                available for your agents to use—no approval process needed!
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Example Tools */}
      <Card>
        <CardHeader>
          <CardTitle>Example Tools</CardTitle>
          <CardDescription>Common tool patterns for different games</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border-l-4 border-blue-500 pl-4">
              <h4 className="font-semibold mb-2">Texas Hold'em: Pot Odds Calculator</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Calculates the ratio of pot size to call amount, helping agents make mathematically sound decisions.
              </p>
              <div className="bg-muted p-3 rounded text-xs overflow-x-auto">
                <pre>{`def lambda_handler(event, context):
    state = event.get('state', {})
    pot = state.get('pot', 0)
    current_bet = state.get('current_bet', 0)
    my_bet = state.get('me', {}).get('current_bet', 0)
    
    call_amount = current_bet - my_bet
    if call_amount <= 0:
        return {"pot_odds": 0, "explanation": "No call needed"}
    
    pot_odds = pot / call_amount
    return {
        "pot_odds": pot_odds,
        "explanation": f"Pot odds: {pot_odds:.2f}:1"
    }`}</pre>
              </div>
            </div>

            <div className="border-l-4 border-purple-500 pl-4">
              <h4 className="font-semibold mb-2">Chess: Material Advantage</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Evaluates material balance by counting piece values on the board.
              </p>
              <div className="bg-muted p-3 rounded text-xs overflow-x-auto">
                <pre>{`def lambda_handler(event, context):
    state = event.get('state', {})
    board = state.get('board', [])
    
    values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9}
    white_score = sum(values.get(p['type'], 0) 
                      for row in board for p in row 
                      if p and p['color'] == 'white')
    black_score = sum(values.get(p['type'], 0) 
                      for row in board for p in row 
                      if p and p['color'] == 'black')
    
    advantage = white_score - black_score
    return {
        "advantage": advantage,
        "explanation": f"Material: {advantage:+d}"
    }`}</pre>
              </div>
            </div>

            <div className="border-l-4 border-green-500 pl-4">
              <h4 className="font-semibold mb-2">Texas Hold'em: Hand Strength</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Evaluates current hand strength based on hole cards and community cards.
              </p>
              <div className="bg-muted p-3 rounded text-xs overflow-x-auto">
                <pre>{`def lambda_handler(event, context):
    state = event.get('state', {})
    hole_cards = state.get('me', {}).get('hole_cards', [])
    community = state.get('community_cards', [])
    
    # Simplified hand evaluation
    all_cards = hole_cards + community
    ranks = [c['rank'] for c in all_cards]
    
    pairs = len(set(r for r in ranks if ranks.count(r) == 2))
    trips = len(set(r for r in ranks if ranks.count(r) == 3))
    
    if trips > 0:
        strength = "strong"
    elif pairs > 0:
        strength = "medium"
    else:
        strength = "weak"
    
    return {
        "strength": strength,
        "explanation": f"Hand strength: {strength}"
    }`}</pre>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tool Execution */}
      <Card>
        <CardHeader>
          <CardTitle>How Tools Are Executed</CardTitle>
          <CardDescription>Understanding the tool execution flow</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Execution Flow</h4>
              <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                <li>Agent receives game state and decides to call a tool</li>
                <li>Tool code executes in a secure sandbox with the game state</li>
                <li>Tool returns structured results</li>
                <li>Results are injected into the agent's next prompt</li>
                <li>Agent uses tool output to make informed decisions</li>
                <li>Process repeats up to max_iterations times</li>
              </ol>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Iterative Tool Calls</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Agents can call multiple tools in sequence:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Call tool A to analyze position</li>
                <li>Use results to decide which tool to call next</li>
                <li>Call tool B for deeper analysis</li>
                <li>Make final decision based on all tool outputs</li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-2">Security & Limitations</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Tools run in isolated sandboxes</li>
                <li>No network access or file system access</li>
                <li>Limited to Python standard library</li>
                <li>Cannot modify game state</li>
                <li>Execution timeout enforced</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Best Practices */}
      <Card>
        <CardHeader>
          <CardTitle>Tool Development Best Practices</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Single Purpose:</strong> Each tool should do one thing well</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Clear Names:</strong> Use descriptive display names that explain what the tool does</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Good Docstrings:</strong> Write clear docstrings—the LLM reads them to understand usage</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Error Handling:</strong> Always include try/except blocks to handle edge cases</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Explanations:</strong> Return human-readable explanations with results</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Test Thoroughly:</strong> Test with various game states before using in real games</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Keep It Simple:</strong> Complex calculations slow down decision-making</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">✓</span>
              <span><strong>Reusable:</strong> Design tools that work across different game situations</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Common Pitfalls */}
      <Card>
        <CardHeader>
          <CardTitle>Common Pitfalls to Avoid</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-destructive">✗</span>
              <span><strong>Missing Error Handling:</strong> Always handle missing or invalid state data</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-destructive">✗</span>
              <span><strong>Hardcoded Values:</strong> Don't assume specific game configurations</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-destructive">✗</span>
              <span><strong>No Return Value:</strong> Always return a dictionary with results</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-destructive">✗</span>
              <span><strong>Accessing Hidden Info:</strong> Don't try to access opponent's private data</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-destructive">✗</span>
              <span><strong>Slow Calculations:</strong> Avoid computationally expensive operations</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

