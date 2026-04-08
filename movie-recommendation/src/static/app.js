function chatBotApp() {
	return {
		messages: [],
		userInput: '',
		selectedGenre: '',
		inputExamples: [
			'Harry Potter defeats Voldemort',
			'Marty McFly meets his parents in the past.',
			'Thanos collects all Infinity Stones'
		],
		validateInput() {
			if (this.userInput.length < 3) {
				this.$refs.errorMessage.style.display = 'block';
				return false;
			}
			this.$refs.errorMessage.style.display = 'none';
			return true;
		},
		handleSend(userMessage, eventName='ui-ready') {
			// this is needed so HTMX will be able to access the input value
			// even if user clicks a quick option button
			// (in which case the input field would be empty)
			this.userInput = userMessage; 

			// validate input
			if (!this.validateInput()) {
				return;
			}

			// build messages layout
			this.messages.push({ type: 'user', content: userMessage });
            this.messages.push({ type: 'bot', content: '' });

			// dispatch event to trigger HTMX request, then clear input after HTMX reads it
			this.$nextTick(() => {
				this.$dispatch(eventName);
				this.userInput = ''; // HTMX already read it during dispatch
			});
		}
	};
		
}
